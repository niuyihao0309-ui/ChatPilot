@echo off
setlocal
title E-Commerce CS - Stop All
cd /d "%~dp0"

REM ===========================================================================
REM  Stops everything start.bat launched.
REM    1) kill processes listening on 18082 / 18081 / 5173
REM    2) close the CS-* service windows
REM    3) stop the MySQL container (the data volume is kept)
REM
REM  IMPORTANT: keep this file PURE ASCII with CRLF line endings.
REM ===========================================================================

echo.
echo ============================================================
echo             E-Commerce CS  -  Stop All Services
echo ============================================================
echo.

echo [1/3] Killing processes on service ports ...
for %%P in (18082 18081 5173) do call :kill_port %%P

echo [2/3] Closing service windows ...
taskkill /F /FI "WINDOWTITLE eq CS-Backend" >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq CS-Commerce" >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq CS-Frontend" >nul 2>nul
echo       done

echo [3/3] Stopping MySQL container ...
docker compose -f "docker\docker-compose.yml" stop

echo.
echo ============================================================
echo   Stopped. Data is kept in the docker volume mysql_data.
echo   To also remove the container and its data, run manually:
echo       docker compose -f docker\docker-compose.yml down -v
echo ============================================================
echo.
echo Press any key to close this window ...
pause >nul
exit /b 0


:kill_port
set /a _found=0
for /f "tokens=5" %%p in ('netstat -ano ^| findstr ":%1 " ^| findstr "LISTENING"') do (
    echo       killing port %1 - PID %%p
    taskkill /F /PID %%p >nul 2>nul
    set /a _found+=1
)
if %_found%==0 echo       port %1: no listener
exit /b 0
