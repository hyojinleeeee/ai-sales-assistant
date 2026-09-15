@echo off
chcp 65001 > NUL
title Server Shutdown
setlocal enabledelayedexpansion

echo.
echo  ====================================================
echo   Stopping servers...
echo  ====================================================
echo.

echo  [1/2] Stopping backend server (port 8004)...
set found=0
for /f "tokens=5" %%a in ('netstat -aon 2^>NUL ^| findstr ":8004 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a > NUL 2>&1
    set found=1
)
if !found! equ 1 (echo  Backend stopped.) else (echo  Backend: not running.)

echo  [2/2] Stopping frontend server (port 5177)...
set found=0
for /f "tokens=5" %%a in ('netstat -aon 2^>NUL ^| findstr ":5177 " ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a > NUL 2>&1
    set found=1
)
if !found! equ 1 (echo  Frontend stopped.) else (echo  Frontend: not running.)

echo.
echo  ====================================================
echo   Servers stopped. Run start_server.bat to restart.
echo  ====================================================
echo.
pause
endlocal
