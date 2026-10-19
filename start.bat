@echo off
setlocal
title E-Commerce CS - Start All
cd /d "%~dp0"

REM ===========================================================================
REM  One-click launcher for the customer-service demo stack.
REM  Steps: Docker -> MySQL container -> backend(18082) -> commerce(18081)
REM         -> frontend Vite(5173) -> open browser
REM  Every service runs in its own window and keeps running after this window
REM  is closed. To stop everything, double-click stop.bat.
REM
REM  IMPORTANT: keep this file PURE ASCII with CRLF line endings.
REM  Non-ASCII bytes together with "chcp 65001" make cmd.exe mis-read the file
REM  and execute fragments of comments as commands.
REM ===========================================================================

set "ROOT=%~dp0"
if "%ROOT:~-1%"=="\" set "ROOT=%ROOT:~0,-1%"

set "BACKEND_PORT=18082"
set "COMMERCE_PORT=18081"
set "FRONTEND_PORT=5273"
set "MYSQL_CONTAINER=customer-service-mysql"
set "COMPOSE_FILE=docker\docker-compose.yml"

echo.
echo ============================================================
echo             E-Commerce CS  -  Start All Services
echo ------------------------------------------------------------
echo    MySQL      container  %MYSQL_CONTAINER%   : 3306
echo    Backend    http://127.0.0.1:%BACKEND_PORT%
echo    Commerce   http://127.0.0.1:%COMMERCE_PORT%
echo    Frontend   http://127.0.0.1:%FRONTEND_PORT%
echo ============================================================
echo.

REM ---------- 0. locate uv (project uses uv for Python deps) ----------
set "UV=uv"
where uv >nul 2>nul
if errorlevel 1 (
    if exist "%USERPROFILE%\.local\bin\uv.exe" (
        set "UV=%USERPROFILE%\.local\bin\uv.exe"
    ) else if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" (
        set "UV=%LOCALAPPDATA%\Programs\uv\uv.exe"
    ) else (
        echo [ERROR] uv not found. Install uv or add it to PATH first:
        echo         https://docs.astral.sh/uv/
        echo.
        pause
        exit /b 1
    )
)
if not exist "%ROOT%\.venv" (
    echo [0/6] .venv missing - running "uv sync" ...
    call "%UV%" sync
)

REM ---------- 1. Docker ----------
echo [1/6] Checking Docker ...
docker info >nul 2>nul
if errorlevel 1 (
    echo       Docker is not running - starting Docker Desktop ...
    if exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" (
        start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
        call :wait_docker
    ) else (
        echo       [ERROR] Docker Desktop not found. Start Docker manually, then retry.
        echo.
        pause
        exit /b 1
    )
) else (
    echo       Docker is running
)

REM ---------- 2. MySQL ----------
echo [2/6] Starting MySQL container ...
docker compose -f "%COMPOSE_FILE%" up -d
if errorlevel 1 (
    echo       [ERROR] Failed to start MySQL container. See the output above.
    echo.
    pause
    exit /b 1
)
echo       waiting for MySQL, first init can take over 30s ...
call :wait_mysql

REM ---------- 3. backend ----------
echo [3/6] Starting backend %BACKEND_PORT% ...
call :port_busy %BACKEND_PORT%
if errorlevel 1 (
    REM Use "python -m uvicorn" instead of bare "uvicorn": the latter goes
    REM through the uv trampoline on Windows and fails in some shells with
    REM "uv trampoline failed to canonicalize script path".
    start "CS-Backend" cmd /k "title CS-Backend && cd /d %ROOT% && %UV% run python -m uvicorn api.app:app --host 127.0.0.1 --port %BACKEND_PORT% --reload"
    echo       started in a separate window
) else (
    echo       port %BACKEND_PORT% already in use - skipped
)

REM ---------- 4. commerce ----------
echo [4/6] Starting commerce service %COMMERCE_PORT% ...
call :port_busy %COMMERCE_PORT%
if errorlevel 1 (
    start "CS-Commerce" cmd /k "title CS-Commerce && cd /d %ROOT%\ecommerce-service-backend && %UV% run python main.py"
    echo       started in a separate window
) else (
    echo       port %COMMERCE_PORT% already in use - skipped
)

REM ---------- 5. frontend ----------
echo [5/6] Starting frontend %FRONTEND_PORT% ...
call :port_busy %FRONTEND_PORT%
if errorlevel 1 (
    if not exist "%ROOT%\customer-service-frontend\node_modules" (
        echo       node_modules missing - running "npm install", may take a while ...
        pushd "%ROOT%\customer-service-frontend"
        call npm install
        popd
    )
    start "CS-Frontend" cmd /k "title CS-Frontend && cd /d %ROOT%\customer-service-frontend && npm run dev"
    echo       started in a separate window
) else (
    echo       port %FRONTEND_PORT% already in use - skipped
)

REM ---------- 6. wait for frontend, then open browser ----------
echo [6/6] Waiting for frontend, then opening browser ...
where curl >nul 2>nul
if errorlevel 1 (
    echo       curl not found - waiting 8s then opening browser
    call :sleep 8
    start "" http://127.0.0.1:%FRONTEND_PORT%
    goto done
)

set /a _wf=0
:wait_front
set /a _wf+=1
curl -s -f -o nul --max-time 3 http://127.0.0.1:%FRONTEND_PORT%
if not errorlevel 1 (
    echo       frontend is up - opening browser ...
    start "" http://127.0.0.1:%FRONTEND_PORT%
    goto done
)
if %_wf% GEQ 30 (
    echo       [WARN] timed out waiting for frontend - open the URL manually
    goto done
)
call :sleep 1
goto wait_front

:done
echo.
echo ============================================================
echo   All services started
echo     API docs   http://127.0.0.1:%BACKEND_PORT%/docs
echo     Frontend   http://127.0.0.1:%FRONTEND_PORT%
echo   Run stop.bat to stop everything.
echo ============================================================
echo.
echo Press any key to close this window - services keep running ...
pause >nul
exit /b 0


REM ===========================================================================
REM                               subroutines
REM ===========================================================================

:wait_docker
set /a _wd=0
:wd_loop
docker info >nul 2>nul
if not errorlevel 1 (
    echo       Docker is ready
    exit /b 0
)
set /a _wd+=1
if %_wd% GEQ 60 (
    echo       [WARN] timed out waiting for Docker - check Docker Desktop
    exit /b 1
)
call :sleep 2
goto wd_loop

:wait_mysql
set /a _wm=0
:wm_loop
set "HEALTH="
for /f "usebackq delims=" %%s in (`docker inspect -f "{{.State.Health.Status}}" %MYSQL_CONTAINER% 2^>nul`) do set "HEALTH=%%s"
if /i "%HEALTH%"=="healthy" (
    echo       MySQL is ready
    exit /b 0
)
set /a _wm+=1
if %_wm% GEQ 45 (
    echo       [WARN] timed out waiting for MySQL - continuing anyway
    exit /b 1
)
call :sleep 2
goto wm_loop

REM return 0 if port %1 is already LISTENING, 1 if it is free
:port_busy
netstat -ano | findstr ":%1 " | findstr "LISTENING" >nul 2>nul
exit /b %errorlevel%

REM sleep about %1 seconds. Uses ping, NOT timeout: timeout errors out when
REM stdin is redirected or there is no console, turning the wait loop into a spin.
:sleep
set /a _sl=%1+1
ping -n %_sl% 127.0.0.1 >nul 2>nul
exit /b 0
