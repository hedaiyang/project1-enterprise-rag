@echo off
REM ============================================================
REM 启动企业级 RAG FastAPI 后端
REM 运行方式：双击这个 .bat 文件，或者在 PyCharm Terminal 里跑
REM ============================================================
cd /d %~dp0
echo ============================================================
echo   启动企业级 RAG 知识库问答系统 (FastAPI + Chroma + Ollama)
echo   访问地址: http://localhost:8000/docs
echo   按 Ctrl+C 停止服务
echo ============================================================
echo.

REM 用已经验证过的 05_RAG\.venv，绕过 Windows 应用控制策略
uv run --project e:\baishan2607c\05_RAG python -m uvicorn main:app --host 0.0.0.0 --port 8000

pause
