@echo off
REM ============================================================
REM  Xiaoer AI Customer Service - Reverse Tunnel
REM  Exposes local backend (18082 / 18081) to the cloud server
REM  so that http://82.157.59.218/ can reach your local Docker.
REM
REM  USAGE: keep this window OPEN while others are visiting.
REM         Closing the window = backend goes offline.
REM ============================================================
title Tunnel - Xiaoer AI Customer Service

set "KEY=%USERPROFILE%\.ssh\itnyh.pem"
set "HOST=root@82.157.59.218"

if not exist "%KEY%" (
    echo.
    echo [ERROR] SSH key not found: %KEY%
    echo         Copy itnyh.pem to %USERPROFILE%\.ssh\ first.
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Reverse tunnel to 82.157.59.218
echo     local 18082  (backend)   --^>  server 18082
echo     local 18081  (commerce)  --^>  server 18081
echo ------------------------------------------------------------
echo   Keep this window open. Press Ctrl+C to stop.
echo ============================================================
echo.

:loop
ssh -N -i "%KEY%" ^
    -o StrictHostKeyChecking=no ^
    -o ServerAliveInterval=30 ^
    -o ServerAliveCountMax=3 ^
    -o ExitOnForwardFailure=yes ^
    -R 18082:127.0.0.1:18082 ^
    -R 18081:127.0.0.1:18081 ^
    %HOST%

echo.
echo   [!] Tunnel dropped. Reconnecting in 5 seconds... (Ctrl+C to quit)
timeout /t 5 /nobreak >nul
goto loop
