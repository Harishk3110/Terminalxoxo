@echo off
setlocal
title KnK Capital Terminal
cd /d "%~dp0apps\terminal-web"
if errorlevel 1 goto failed

where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is not available. Install Node.js and open this launcher again.
  goto failed
)

set "KNK_NEXT_DIST_DIR=.next"
set "KNK_API_URL=http://127.0.0.1:8000"
set "NEXT_PUBLIC_APP_ENV=local"
if not exist "%KNK_NEXT_DIST_DIR%\BUILD_ID" (
  echo The verified terminal build is missing.
  echo Run the build instructions in README.md first.
  goto failed
)

echo Starting KnK Capital Terminal...
echo Keep this window open while using the terminal.
echo After the Ready message, paste this address into Firefox:
echo http://127.0.0.1:3001/overview
echo.
node "node_modules\next\dist\bin\next" start --hostname 127.0.0.1 --port 3001 --keepAliveTimeout 70000
if errorlevel 1 goto failed
exit /b 0

:failed
echo.
echo The terminal could not start. The error is shown above.
pause
exit /b 1
