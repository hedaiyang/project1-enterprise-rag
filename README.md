# 企业级智能问答 RAG 系统（Advanced RAG）

面向工业数控机床故障诊断的企业级知识库问答系统。相比 Naive RAG 基线，本项目补齐了混合检索、元数据权限过滤、SSE 流式输出、Redis 缓存与 JWT 鉴权，并在同一批数据上完成了量化评测。

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Python 3.11、FastAPI、Uvicorn |
| 前端 | Vue 3、Vite、Element Plus、Vue Router、Axios |
| 检索 | Chroma（向量库）、BM25（jieba 中文分词）、RRF 融合 |
| 模型 | Ollama 本地部署：`bge-m3` 向量化 + `qwen2.5:3b` 生成 |
| 可选增强 | Redis 缓存、PyJWT 鉴权（未安装时自动降级，不影响核心功能） |

## 核心能力

1. **混合检索**：向量 Top5 + BM25 Top5，RRF 融合后统一排序
2. **元数据过滤**：每个 chunk 带 `source` / `device` / `security_level`，检索时按设备型号 + 密级双重过滤
3. **权限隔离**：admin 可见 V1 + V2，worker 仅可见 V1（metadata 即权限维度，无需独立权限表）
4. **SSE 流式输出**：首 token 快速返回，末尾附带结构化来源
5. **Redis 缓存**：热门问题 24h 缓存；文档入库/删除时自动失效
6. **JWT 鉴权**：登录签发 token，接口按角色过滤

## 目录结构

```
project1-enterprise-rag/
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── api/routes.py           # 7 个接口
│   ├── core/
│   │   ├── config.py           # 全局配置（环境变量可覆盖）
│   │   ├── parser.py           # 文档解析 + 分块
│   │   ├── vectorstore.py      # Chroma 封装 + where 条件转换
│   │   ├── retriever.py        # 向量 + BM25 混合检索
│   │   ├── rag.py              # Prompt 拼装 + 生成 + 流式
│   │   └── auth_cache.py       # JWT 鉴权 + Redis 缓存（全降级）
│   ├── scripts/
│   │   ├── eval.py             # 检索评测（Recall@K）
│   │   └── sync_from_mysql.py  # 模拟从 MySQL 同步维修记录
│   └── data/
│       ├── raw/                # 原始文档
│       │   ├── CK6132.md       # 普通车床故障手册（10 条）
│       │   ├── CK6140.md       # 数控车床故障手册（10 条）
│       │   ├── VMC850.md       # 立式加工中心故障手册（10 条）
│       │   └── V2_机密技术通告.md
│       └── chroma_db/          # 向量库持久化目录
└── frontend/
    └── src/
        ├── api/index.js        # 接口封装 + JWT 拦截器
        ├── router/index.js     # 路由 + 登录守卫
        └── views/
            ├── Login.vue       # 登录
            ├── Dashboard.vue   # 系统概览
            ├── Chat.vue        # 智能问答（SSE）
            └── Documents.vue   # 文档上传 / 删除
```

## 接口列表

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/login` | 登录获取 JWT（FormData） | 公开 |
| GET | `/api/health` | 健康检查 + chunk 数量 | 公开 |
| POST | `/api/ingest` | 上传文档入库（`file` + `device` + `security_level`） | V2 仅 admin |
| POST | `/api/query` | 同步问答（带缓存） | 按角色过滤 |
| POST | `/api/query/stream` | SSE 流式问答 | 按角色过滤 |
| GET | `/api/sources` | 已入库文档列表 | 按角色过滤 |
| DELETE | `/api/sources/{source}` | 删除指定源文档 | 仅 admin |

登录账号：`admin / 123`（管理员），其他任意用户名 / `123`（普通工人）。

## 快速启动

### 1. 启动 Ollama 并拉取模型

```bash
ollama pull bge-m3
ollama pull qwen2.5:3b
```

### 2. 后端

```powershell
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

打开 http://localhost:8000/docs 查看 Swagger。

### 3. 前端

```powershell
cd frontend
npm install
npm run dev
```

打开 http://localhost:5173，用 `admin / 123` 登录。

### 4. 运行评测

```powershell
cd backend
python scripts/eval.py
```

## 评测结果（与 Naive RAG 对比）

| 指标 | Naive RAG | Advanced RAG |
|------|-----------|--------------|
| Recall@5 | 35% | 80% |
| 跨设备误召回 | 常见（无 metadata 过滤） | 基本消除（device 精确过滤） |
| 平均响应时间 | ~3s | ~10ms（Redis 缓存命中） |

> 评测方法：`scripts/eval.py`，10 条标答问题，按设备型号过滤后做关键词命中判定。样本量较小，仅用于基线对比。

## 工程降级设计

- **Rerank**：`bge-reranker-v2-m3` 在 Windows 下加载 DLL 被应用控制策略拦截，`config.py` 中 `USE_RERANK=false`，代码保留，Linux 生产环境可直接开启
- **Redis / PyJWT**：未安装时自动跳过缓存与鉴权，核心检索问答不受影响

## 与 Naive RAG 的差异

| 维度 | Naive RAG | 本项目 |
|------|-----------|--------|
| 检索 | 纯向量 TopK | 向量 + BM25 + RRF 融合 |
| 元数据 | 无 | source / device / security_level |
| 权限 | 无 | JWT + 角色级 metadata 过滤 |
| 输出 | 一次性返回 | SSE 流式 |
| 缓存 | 无 | Redis 24h（写入自动失效） |
| 前端 | Streamlit | Vue3 + FastAPI 前后端分离 |
