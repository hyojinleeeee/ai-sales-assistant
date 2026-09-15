@echo off
chcp 65001 > NUL
title AI Sales Assistant

set BASE=%~dp0
set FRONTEND=%BASE%frontend
set BACKEND=%BASE%backend
set PYTHONUTF8=1

echo.
echo  ====================================================
echo   AI Sales Assistant - Starting...
echo  ====================================================
echo.

echo  [1/4] Installing Python packages if needed...
pip install -r %BACKEND%\requirements.txt -q
echo        Done.
echo.

echo  [2/4] Installing Node.js packages if needed...
if not exist %FRONTEND%\node_modules cmd /c "cd /d %FRONTEND% && npm install --silent"
echo        Done.
echo.

echo  [3/4] Starting backend server (port 8004)...
start "Backend Server - port 8004" cmd /k "cd /d %BACKEND% && python main.py"
timeout /t 3 /nobreak > NUL

echo  [4/4] Starting frontend server (port 5177)...
start "Frontend Server - port 5177" cmd /k "cd /d %FRONTEND% && npm run dev"

echo.
echo  Waiting for servers to start...
timeout /t 7 /nobreak > NUL
start http://localhost:5177

echo.
echo  ====================================================
echo   AI Sales Assistant is running!  URL: http://localhost:5177
echo   Demo accounts: admin/1234 (관리자), sls001~sls040/1234 (조직원)
echo.
echo   To stop: run shutdown_server.bat
echo  ====================================================
echo.
pause > NUL
