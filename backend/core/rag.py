"""RAG 生成链路 —— 检索 → 拼 Prompt → LLM 生成"""
import json

from langchain_ollama import ChatOllama
from langchain_core.documents import Document
from core import config as cfg
from core.retriever import hybrid_search


SYSTEM_PROMPT = """你是工业设备故障诊断专家。严格根据【检索到的文档片段】回答问题。

规则：
1. 只使用文档中的信息，禁止编造
2. 文档中出现具体型号、参数、金额、零部件名称时，必须原样引用，不要概括或省略
3. 文档确实没有相关信息时，才回答「知识库中暂未找到相关内容」
4. 回答分点列明：可能原因 → 排查步骤 → 解决方案
5. 结尾标注引用了哪些片段编号"""


def build_context(docs: list[Document]) -> str:
    """把检索到的文档片段拼成上下文字符串"""
    parts = []
    for i, doc in enumerate(docs, 1):
        meta_info = ""
        if doc.metadata:
            meta_info = f"（来源：{doc.metadata.get('source', '未知')} | 设备：{doc.metadata.get('device', '通用')}）"
        parts.append(f"【片段{i}】{meta_info}\n{doc.page_content}")
    return "\n\n".join(parts)


def format_prompt(query: str, context: str) -> str:
    return f"{SYSTEM_PROMPT}\n\n【检索到的文档片段】\n{context}\n\n【用户问题】\n{query}\n\n【回答】"


def answer(query: str, metadata_filter: dict = None) -> dict:
    """同步问答 —— 返回完整答案 + 检索来源"""
    docs = hybrid_search(query, metadata_filter)
    context = build_context(docs)
    prompt = format_prompt(query, context)

    llm = ChatOllama(model=cfg.LLM_MODEL, base_url=cfg.OLLAMA_BASE_URL, temperature=0.1)
    response = llm.invoke(prompt)

    return {
        "answer": response.content,
        "sources": [
            {
                "content": d.page_content,
                "metadata": d.metadata,
                "rerank_score": d.metadata.get("rerank_score"),
            }
            for d in docs
        ],
        "retrieval_config": {
            "top_k": cfg.TOP_K,
            "use_bm25": cfg.USE_BM25,
            "use_rerank": cfg.USE_RERANK,
            "chunk_size": cfg.CHUNK_SIZE,
        },
    }


async def answer_stream(query: str, metadata_filter: dict = None):
    """SSE 流式问答 —— 逐 token yield"""
    docs = hybrid_search(query, metadata_filter)
    context = build_context(docs)
    prompt = format_prompt(query, context)

    llm = ChatOllama(model=cfg.LLM_MODEL, base_url=cfg.OLLAMA_BASE_URL, temperature=0.1)
    async for chunk in llm.astream(prompt):
        yield chunk.content

    # 最后 yield 来源信息（结构化 JSON，前端解析后渲染，避免前端二次请求）
    yield "\n\n---\n"
    for i, d in enumerate(docs, 1):
        meta_info = d.metadata.get("source", "未知") if d.metadata else "未知"
        yield f"[{i}] 来源: {meta_info}\n"
    payload = [
        {
            "content": d.page_content,
            "metadata": d.metadata,
            "rerank_score": d.metadata.get("rerank_score") if d.metadata else None,
        }
        for d in docs
    ]
    yield "__SOURCES__" + json.dumps(payload, ensure_ascii=False, default=str)
