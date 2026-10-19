@echo off
setlocal enableextensions
title Xiaoer - Deploy to Server
cd /d "%~dp0"

REM ===========================================================================
REM  One-click deploy: local  ->  cloud server (82.157.59.218)
REM    1. build frontend        npm run build
REM    2. upload frontend       -> /var/www/xiaoer    (tar + scp + atomic swap)
REM    3. sync backend code     -> /opt/xiaoer        (tar, excludes junk)
REM    4. restart backend services
REM
REM  IMPORTANT: keep this file PURE ASCII with CRLF line endings.
REM  Non-ASCII bytes together with "chcp 65001" make cmd.exe mis-read the file
REM  and execute fragments of comments as commands.
REM ===========================================================================

set "SRV=root@82.157.59.218"
set "KEY=%USERPROFILE%\.ssh\itnyh.pem"
set "NPM=C:\Program Files\nodejs\npm.cmd"

REM --- Use the Windows built-ins by ABSOLUTE path. -------------------------
REM If a Git-for-Windows install sits earlier on PATH it shadows these with
REM MSYS builds, which treat a backslash as an escape character: the path
REM "dist\*" silently turns into "dist*" and scp then fails with
REM 'stat local "...dist*": No such file or directory'.
set "TAR=%SystemRoot%\System32\tar.exe"
set "SSHEXE=%SystemRoot%\System32\OpenSSH\ssh.exe"
set "SCPEXE=%SystemRoot%\System32\OpenSSH\scp.exe"
if not exist "%TAR%"    set "TAR=tar"
if not exist "%SSHEXE%" set "SSHEXE=ssh"
if not exist "%SCPEXE%" set "SCPEXE=scp"

REM Forward-slash copies of Windows paths, safe for both implementations.
set "KEYU=%KEY:\=/%"
set "TMPU=%TEMP:\=/%"
set "SSHOPT=-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=20"

if not exist "%KEY%" (
    echo [ERROR] SSH key not found: %KEY%
    pause
    exit /b 1
)

echo.
echo ============================================================
echo              Deploy  Xiaoer  -^>  %SRV%
echo ------------------------------------------------------------
echo   1  frontend  build + upload  -^>  /var/www/xiaoer
echo   2  backend   code sync       -^>  /opt/xiaoer
echo   3  restart   backend services
echo ============================================================
echo.

REM ---------------------------------------------------------------- 1/4
echo [1/4] Building frontend ...
pushd customer-service-frontend
call "%NPM%" run build
if errorlevel 1 (
    echo.
    echo [ERROR] Frontend build failed. Nothing was uploaded.
    popd
    pause
    exit /b 1
)
popd
echo       build ok
echo.

REM ---------------------------------------------------------------- 2/4
echo [2/4] Uploading frontend ...
"%TAR%" -czf "%TEMP%\xiaoer-dist.tgz" -C customer-service-frontend dist
if errorlevel 1 ( echo [ERROR] tar failed. & pause & exit /b 1 )
"%SCPEXE%" -i "%KEYU%" %SSHOPT% "%TMPU%/xiaoer-dist.tgz" %SRV%:/tmp/
if errorlevel 1 ( echo [ERROR] scp failed. & pause & exit /b 1 )
"%SSHEXE%" -i "%KEYU%" %SSHOPT% %SRV% "rm -rf /var/www/xiaoer.new && mkdir -p /var/www/xiaoer.new && tar xzf /tmp/xiaoer-dist.tgz -C /var/www/xiaoer.new --strip-components=1 && rm -rf /var/www/xiaoer.old && mv /var/www/xiaoer /var/www/xiaoer.old && mv /var/www/xiaoer.new /var/www/xiaoer && rm -f /tmp/xiaoer-dist.tgz"
if errorlevel 1 ( echo [ERROR] remote step failed. & pause & exit /b 1 )
echo       upload ok
echo.

REM ---------------------------------------------------------------- 3/4
echo [3/4] Syncing backend code ...
REM sp / 01 / outputs are teaching material (gitignored) - must NOT go up.
REM task/ is REAL source code (plan/models.py imports task.command.models),
REM so never add it to the exclude list.
"%TAR%" -czf "%TEMP%\xiaoer-src.tgz" ^
    --exclude=.venv ^
    --exclude=.git ^
    --exclude=.idea ^
    --exclude=.workbuddy ^
    --exclude=sp ^
    --exclude=01 ^
    --exclude=outputs ^
    --exclude=node_modules ^
    --exclude=dist ^
    --exclude=__pycache__ ^
    --exclude=customer-service-frontend ^
    .
if errorlevel 1 ( echo [ERROR] tar failed. & pause & exit /b 1 )
"%SCPEXE%" -i "%KEYU%" %SSHOPT% "%TMPU%/xiaoer-src.tgz" %SRV%:/tmp/
if errorlevel 1 ( echo [ERROR] scp failed. & pause & exit /b 1 )
"%SSHEXE%" -i "%KEYU%" %SSHOPT% %SRV% "tar xzf /tmp/xiaoer-src.tgz -C /opt/xiaoer && rm -f /tmp/xiaoer-src.tgz"
if errorlevel 1 ( echo [ERROR] remote extract failed. & pause & exit /b 1 )
echo       sync ok
echo.

REM ---------------------------------------------------------------- 4/4
echo [4/4] Restarting backend services ...
"%SSHEXE%" -i "%KEYU%" %SSHOPT% %SRV% "systemctl restart xiaoer-backend xiaoer-commerce && sleep 4 && systemctl is-active xiaoer-backend xiaoer-commerce"
if errorlevel 1 ( echo [WARN] restart reported an error - check server logs. )

del /q "%TEMP%\xiaoer-dist.tgz" >nul 2>nul
del /q "%TEMP%\xiaoer-src.tgz"  >nul 2>nul

echo.
echo ============================================================
echo   Done.   http://82.157.59.218/
echo ------------------------------------------------------------
echo   Backend log : ssh -i "%KEYU%" %SRV% "journalctl -u xiaoer-backend -n 50"
echo   Admin panel : http://82.157.59.218/__gate/admin
echo ============================================================
echo.
pause
