"""FastAPI 路由 —— 文档上传/入库、问答、健康检查
补强：Redis 热门问题缓存 + JWT 鉴权 + 角色权限过滤
"""
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Header
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import tempfile
import os

from core.parser import parse_file, split_text
from core.vectorstore import add_documents, get_vectorstore
from core.rag import answer, answer_stream
from core.auth_cache import (
    verify_token,
    role_to_metadata_filter,
    redis_cache,
    clear_query_cache,
    REDIS_AVAILABLE,
    JWT_AVAILABLE,
    create_token,
)

router = APIRouter(prefix="/api", tags=["RAG"])


# ========== 请求/响应模型 ==========
class QueryRequest(BaseModel):
    query: str
    device: str = None  # 可选的设备型号过滤


class QueryResponse(BaseModel):
    answer: str
    sources: list
    retrieval_config: dict
    from_cache: bool = False  # 是否来自 Redis 缓存


# ========== 0. 登录（获取 JWT token） ==========
@router.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    """简单登录接口（演示用，生产应该查数据库）"""
    # 演示：admin/123 → 车间主任权限，其他 → 普通工人
    if username == "admin" and password == "123":
        role = "admin"
    else:
        role = "worker"
    token = create_token(username, role)
    return {
        "token": token,
        "role": role,
        "jwt_available": JWT_AVAILABLE,
        "hint": "把 token 放到请求 Header 的 Authorization 字段",
    }


# ========== 1. 健康检查 ==========
@router.get("/health")
def health():
    vs = get_vectorstore()
    return {
        "status": "ok",
        "collection": vs._collection.name,
        "total_chunks": vs._collection.count(),
        "redis_available": REDIS_AVAILABLE,
        "jwt_available": JWT_AVAILABLE,
        "enhancements": ["混合检索", "metadata过滤", "SSE流式", "Redis缓存(可选)", "JWT鉴权(可选)"],
    }


# ========== 2. 文档上传入库 ==========
@router.post("/ingest")
async def ingest(
    file: UploadFile = File(...),
    device: str = Form(None, description="设备型号（可选，用于 metadata 过滤）"),
    security_level: str = Form("V1", description="密级：V1 普通 / V2 机密"),
    authorization: str = Header(None, description="JWT token"),
):
    """上传文档 → 解析 → 分块 → 入库（带 metadata）"""
    user = verify_token(authorization.replace("Bearer ", "") if authorization else None)
    # 只有 admin 能上传 V2 机密文档
    if security_level == "V2" and user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有 admin 能上传密级 V2 的文档")

    suffix = os.path.splitext(file.filename or "doc.md")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        text = parse_file(tmp_path)
        chunks = split_text(text, source=file.filename or "unknown", device=device, security_level=security_level)
        add_documents(chunks)
        cleared = clear_query_cache()  # 清掉旧问答缓存，避免用户搜不到新入库内容
        return {
            "status": "ok",
            "filename": file.filename,
            "chunks_added": len(chunks),
            "device": device,
            "security_level": security_level,
            "uploaded_by": user.get("user_id"),
            "total_in_collection": get_vectorstore()._collection.count(),
            "cache_cleared": cleared,
        }
    finally:
        os.unlink(tmp_path)


# ========== 3. 同步问答（带 Redis 缓存） ==========
@router.post("/query", response_model=QueryResponse)
def query(req: QueryRequest, authorization: str = Header(None)):
    # JWT 鉴权 → 角色权限过滤
    token = authorization.replace("Bearer ", "") if authorization else None
    user = verify_token(token)
    base_filter = {"device": req.device} if req.device and req.device != "通用" else None
    metadata_filter = role_to_metadata_filter(user.get("role"), base_filter)

    # Redis 缓存 key：query + device + role
    cache_key_raw = f"{req.query}|{req.device or 'all'}|{user.get('role')}"
    cache_hit = False
    cached_result = None

    if REDIS_AVAILABLE:
        import hashlib
        import json as _json
        key = f"rag:query:{hashlib.md5(cache_key_raw.encode()).hexdigest()}"
        try:
            import redis
            r = redis.Redis()
            cached = r.get(key)
            if cached:
                cached_result = _json.loads(cached)
                cache_hit = True
                print(f"🎯 Redis 缓存命中: {req.query[:40]}")
        except Exception:
            pass

    if cached_result:
        cached_result["from_cache"] = True
        return cached_result

    # 缓存未命中 → 正常检索生成
    try:
        result = answer(req.query, metadata_filter)
        result["from_cache"] = False
        # 写入 Redis 缓存
        if REDIS_AVAILABLE:
            try:
                r = redis.Redis()
                r.setex(key, 86400, _json.dumps(result, ensure_ascii=False, default=str))
            except Exception:
                pass
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ========== 4. SSE 流式问答 ==========
@router.post("/query/stream")
async def query_stream(req: QueryRequest, authorization: str = Header(None)):
    # JWT 鉴权 → 角色权限过滤（与同步接口保持一致，防止越权看机密文档）
    token = authorization.replace("Bearer ", "") if authorization else None
    user = verify_token(token)
    base_filter = {"device": req.device} if req.device and req.device != "通用" else None
    metadata_filter = role_to_metadata_filter(user.get("role"), base_filter)

    async def generate():
        async for token in answer_stream(req.query, metadata_filter):
            # SSE 格式: data: xxx\n\n
            yield f"data: {token}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


# ========== 5. 列出所有源文档 ==========
@router.get("/sources")
def list_sources(authorization: str = Header(None)):
    """按角色过滤：admin 看全部，worker 看不到 V2 机密文档名"""
    user = verify_token(authorization.replace("Bearer ", "") if authorization else None)
    is_admin = user.get("role") == "admin"
    vs = get_vectorstore()
    total = vs._collection.count()
    if total == 0:
        return {"sources": [], "total_chunks": 0, "role": user.get("role")}
    all_data = vs._collection.get(limit=total, include=["metadatas"])
    sources = set()
    for m in all_data["metadatas"]:
        if not m or not m.get("source"):
            continue
        if not is_admin and m.get("security_level") == "V2":
            continue  # 普通工人不可见机密文档
        sources.add(m["source"])
    return {"sources": sorted(sources), "total_chunks": total, "role": user.get("role")}


# ========== 6. 删除指定源文档 ==========
@router.delete("/sources/{source}")
def delete_source(source: str, authorization: str = Header(None)):
    """删除指定源文档的所有 chunk（仅 admin）"""
    user = verify_token(authorization.replace("Bearer ", "") if authorization else None)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="只有 admin 能删除文档")
    vs = get_vectorstore()
    # 找出所有匹配的 IDs
    total = vs._collection.count()
    all_data = vs._collection.get(limit=total, include=["metadatas"])
    ids_to_delete = [
        all_data["ids"][i]
        for i, m in enumerate(all_data["metadatas"])
        if m and m.get("source") == source
    ]
    if not ids_to_delete:
        return {"status": "ok", "deleted": 0, "message": f"没找到 source={source} 的 chunk"}
    vs._collection.delete(ids=ids_to_delete)
    clear_query_cache()  # 文档删除后清缓存，避免答案还引用已删内容
    return {
        "status": "ok",
        "deleted": len(ids_to_delete),
        "source": source,
        "total_chunks": vs._collection.count(),
    }
