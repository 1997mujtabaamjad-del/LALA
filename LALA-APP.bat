@echo off
rem ============================================================
rem  LALA Desktop App — one double-click.
rem  Starts the Electron desktop window; the window itself
rem  auto-starts the Python brain (Ollama answers, tools, memory).
rem ============================================================
cd /d "%~dp0"

if not exist .venv (
  echo ✖ Not installed yet — double-click "install" first, then me.
  pause
  exit /b 1
)

if not exist node_modules (
  echo First run: installing the desktop engine (one-time, a few minutes)...
  call npm install -q --no-audit --no-fund
  if not exist node_modules (
    echo ✖ npm install failed — is Node installed? Get it from nodejs.org
    pause
    exit /b 1
  )
)

echo Starting LALA desktop app...
start "LALA desktop" /min cmd /c "npm start"
exit /b 0
