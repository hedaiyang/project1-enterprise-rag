"""Chroma 向量库封装 —— 统一管理加载/入库/检索"""
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
import core.config as cfg

_embed = None
_vectorstore = None


def get_embeddings() -> OllamaEmbeddings:
    """单例获取 Embedding 模型"""
    global _embed
    if _embed is None:
        _embed = OllamaEmbeddings(model=cfg.EMBED_MODEL, base_url=cfg.OLLAMA_BASE_URL)
    return _embed


def get_vectorstore() -> Chroma:
    """单例获取 Chroma 实例"""
    global _vectorstore
    if _vectorstore is None:
        _vectorstore = Chroma(
            persist_directory=cfg.VECTORSTORE_DIR,
            embedding_function=get_embeddings(),
            collection_name=cfg.COLLECTION_NAME,
        )
    return _vectorstore


def add_documents(docs: list[Document]) -> None:
    """入库：文档 → 分块 → 向量化 → Chroma"""
    vs = get_vectorstore()
    vs.add_documents(docs)


def _to_chroma_where(filter_dict: dict) -> dict:
    """把多字段 filter 转成 Chroma where 语法：
    {"device": "CK6132", "security_level": "V1"} → {"$and": [{"device": "CK6132"}, {"security_level": "V1"}]}
    单字段保持原样：{"device": "CK6132"} → {"device": "CK6132"}
    """
    if not filter_dict or len(filter_dict) <= 1:
        return filter_dict
    return {"$and": [{k: v} for k, v in filter_dict.items()]}


def similarity_search(query: str, k: int = None, filter_dict: dict = None) -> list[Document]:
    """纯向量检索（支持 metadata 过滤）"""
    vs = get_vectorstore()
    kwargs = {"k": k or cfg.TOP_K}
    if filter_dict:
        kwargs["filter"] = _to_chroma_where(filter_dict)
    return vs.similarity_search(query, **kwargs)
