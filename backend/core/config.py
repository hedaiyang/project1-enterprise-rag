"""全局配置 —— 环境变量可覆盖"""
import os

# ========== Ollama ==========
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "bge-m3")        # 向量化模型
LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")       # 生成模型
RERANK_MODEL = os.getenv("RERANK_MODEL", "BAAI/bge-reranker-v2-m3")  # Rerank 模型（本地）

# ========== Chroma 向量库 ==========
VECTORSTORE_DIR = os.getenv("VECTORSTORE_DIR", "data/chroma_db")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "enterprise_knowledge")

# ========== 检索参数 ==========
TOP_K = int(os.getenv("TOP_K", "5"))            # 向量检索返回条数
BM25_K = int(os.getenv("BM25_K", "5"))          # BM25 返回条数
RERANK_TOP_N = int(os.getenv("RERANK_TOP_N", "3"))  # Rerank 二次排序后取前几条
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))

# ========== 入库模式开关 ==========
USE_BM25 = os.getenv("USE_BM25", "true").lower() == "true"        # 混合检索
USE_RERANK = os.getenv("USE_RERANK", "false").lower() == "true"    # Rerank 二次排序（Windows 策略会拦 DLL，默认关）
USE_FLOW = os.getenv("USE_FLOW", "true").lower() == "true"        # SSE 流式输出
