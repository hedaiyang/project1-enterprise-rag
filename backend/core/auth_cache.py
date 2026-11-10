"""Redis 缓存 + JWT 鉴权工具 —— 全降级设计，没装 Redis/没配 SECRET_KEY 就自动跳过"""
import os
import hashlib
import json
import time
from functools import wraps

# ========== Redis 缓存（可选） ==========
try:
    import redis
    _redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        decode_responses=True,
    )
    # 测试连接
    _redis_client.ping()
    REDIS_AVAILABLE = True
except Exception:
    _redis_client = None
    REDIS_AVAILABLE = False
    print("⚠️  Redis 未连接（没装或没启动），缓存功能自动跳过")


CACHE_TTL = int(os.getenv("CACHE_TTL", "86400"))  # 默认缓存 24 小时


def cache_key(*args, **kwargs):
    """把函数参数转成 hash 作为缓存 key"""
    raw = f"{args}{sorted(kwargs.items())}"
    return f"rag:cache:{hashlib.md5(raw.encode()).hexdigest()}"


def redis_cache(func):
    """装饰器：给函数加 Redis 缓存，Redis 不可用时直接执行原函数"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not REDIS_AVAILABLE:
            return func(*args, **kwargs)
        # 查缓存
        key = cache_key(func.__name__, *args, **kwargs)
        cached = _redis_client.get(key)
        if cached:
            print(f"🎯 Redis 缓存命中: {key[:40]}...")
            return json.loads(cached)
        # 缓存未命中，执行原函数
        result = func(*args, **kwargs)
        # 写入缓存（只缓存 dict/list 结果）
        if isinstance(result, (dict, list)):
            _redis_client.setex(key, CACHE_TTL, json.dumps(result, ensure_ascii=False))
        return result
    return wrapper


# ========== JWT 鉴权（可选） ==========
try:
    import jwt  # pip install PyJWT
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
    JWT_ALGORITHM = "HS256"
    JWT_AVAILABLE = True
except ImportError:
    JWT_SECRET = None
    JWT_AVAILABLE = False
    print("⚠️  PyJWT 未安装（pip install PyJWT），鉴权功能自动跳过")


def create_token(user_id: str, role: str = "worker") -> str:
    """生成 JWT token"""
    if not JWT_AVAILABLE:
        return "no-jwt"
    payload = {"user_id": user_id, "role": role, "exp": int(time.time()) + 3600}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """验证 JWT token，返回用户信息；未配置鉴权时返回默认用户"""
    if not JWT_AVAILABLE or token == "no-jwt":
        return {"user_id": "dev-user", "role": "admin"}
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except Exception:
        return {"user_id": "anonymous", "role": "worker"}


def role_to_metadata_filter(role: str, original_filter: dict = None) -> dict:
    """根据用户角色生成 metadata 过滤条件：
    - admin / 车间主任 → 看所有文档
    - worker / 普通工人 → 只能看 security_level=V1 的文档
    """
    flt = dict(original_filter) if original_filter else {}
    if JWT_AVAILABLE and role not in ("admin",):
        # 加密级过滤
        flt["security_level"] = "V1"
    return flt


def clear_query_cache() -> int:
    """清空所有问答缓存 —— 文档入库/删除后必须调用，否则用户看不到新内容"""
    if not REDIS_AVAILABLE:
        return 0
    try:
        keys = list(_redis_client.scan_iter("rag:query:*"))
        if keys:
            _redis_client.delete(*keys)
        return len(keys)
    except Exception:
        return 0
