@echo off
REM Start Vue3 frontend dev server
cd /d %~dp0
echo ========================================
echo   Starting Vue3 Frontend (Vite + Element Plus)
echo   Access: http://localhost:5173
echo   Proxy:  /api -> http://localhost:8000
echo ========================================
call npm run dev
pause
