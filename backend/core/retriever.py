"""混合检索 —— 向量检索 + BM25 + Rerank 二次排序"""
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document
from core import config as cfg
from core.vectorstore import similarity_search, _to_chroma_where


def _tokenize(text: str) -> list[str]:
    """中文分词：优先 jieba，没装就退化为字符级切分"""
    try:
        import jieba
        return list(jieba.cut(text))
    except ImportError:
        # 退化为字符级切分（中文每个字当一个 token，英文按空格）
        tokens = []
        for part in text.split():
            if any("\u4e00" <= ch <= "\u9fff" for ch in part):
                tokens.extend(list(part))  # 中文按字切
            else:
                tokens.append(part)  # 英文/数字整体
        return tokens


def bm25_search(query: str, all_chunks: list[Document], k: int = None) -> list[Document]:
    """BM25 关键词检索（从 Chroma 拉全量 chunk 后本地检索）"""
    k = k or cfg.BM25_K
    tokenized_corpus = [_tokenize(d.page_content) for d in all_chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    scores = bm25.get_scores(_tokenize(query))
    # 取 top k 的索引
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    return [all_chunks[i] for i in top_indices]


def rrf_fusion(vector_docs: list[Document], bm25_docs: list[Document], k: int = 60) -> list[Document]:
    """RRF（Reciprocal Rank Fusion）融合两路检索结果"""
    scores = {}
    for rank, doc in enumerate(vector_docs):
        key = doc.page_content[:80]  # 用前 80 字符去重
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
    for rank, doc in enumerate(bm25_docs):
        key = doc.page_content[:80]
        scores[key] = scores.get(key, 0) + 1.0 / (k + rank + 1)
    # 按融合分数排序，返回融合后的文档列表
    merged = list({d.page_content[:80]: d for d in vector_docs + bm25_docs}.values())
    merged.sort(key=lambda d: scores.get(d.page_content[:80], 0), reverse=True)
    return merged


def rerank(query: str, docs: list[Document], top_n: int = None) -> list[Document]:
    """Rerank 二次排序 —— 用 bge-reranker-v2-m3 对检索结果重新打分"""
    from FlagEmbedding import FlagReranker
    top_n = top_n or cfg.RERANK_TOP_N
    reranker = FlagReranker(cfg.RERANK_MODEL, use_fp16=True)
    pairs = [[query, d.page_content] for d in docs]
    scores = reranker.compute_score(pairs)
    for doc, score in zip(docs, scores):
        doc.metadata["rerank_score"] = float(score)
    docs.sort(key=lambda d: d.metadata.get("rerank_score", 0), reverse=True)
    return docs[:top_n]


def hybrid_search(query: str, metadata_filter: dict = None) -> list[Document]:
    """混合检索主入口
    链路：向量检索 → (+ BM25 融合) → (+ Rerank 二次排序)
    """
    # Step1: 纯向量检索
    vector_docs = similarity_search(query, k=cfg.TOP_K, filter_dict=metadata_filter)

    # Step2: BM25 融合（可选开关）
    if cfg.USE_BM25:
        # 从 Chroma 拉（可选 metadata 过滤后）的 chunk 做 BM25
        from core.vectorstore import get_vectorstore
        vs = get_vectorstore()
        total = vs._collection.count()
        if metadata_filter:
            all_chunks = vs._collection.get(where=_to_chroma_where(metadata_filter), limit=total, include=["documents", "metadatas"])
        else:
            all_chunks = vs._collection.get(limit=total, include=["documents", "metadatas"])
        chunk_docs = [
            Document(page_content=c, metadata=m or {})
            for c, m in zip(all_chunks["documents"], all_chunks["metadatas"])
        ]
        bm25_docs = bm25_search(query, chunk_docs, k=cfg.BM25_K)
        fused = rrf_fusion(vector_docs, bm25_docs)
    else:
        fused = vector_docs

    # Step3: Rerank 二次排序（可选开关）
    if cfg.USE_RERANK and fused:
        fused = rerank(query, fused, top_n=cfg.RERANK_TOP_N)

    return fused
