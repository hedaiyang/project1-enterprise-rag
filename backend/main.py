"""FastAPI 入口 —— 企业级 RAG 知识库问答系统"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(
    title="企业级 RAG 知识库问答系统",
    description="基于 FastAPI + Chroma + Ollama 的混合检索 RAG，支持文档上传、混合检索、Rerank、SSE 流式问答",
    version="1.0.0",
)

# CORS —— 允许前端 Vue3 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发阶段全开，生产环境要收窄
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
def root():
    return {
        "name": "企业级 RAG 知识库问答系统",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "GET  /health": "健康检查",
            "POST /api/ingest": "上传文档入库",
            "POST /api/query": "同步问答",
            "POST /api/query/stream": "SSE 流式问答",
            "GET  /api/sources": "列出所有源文档",
        },
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
