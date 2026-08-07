@echo off
rem ============================================================
rem  LALA Desktop App — double-click me from ANYWHERE.
rem  Finds your LALA folder by itself, starts the brain quietly,
rem  and opens the real desktop window with the brain logo.
rem ============================================================
setlocal enabledelayedexpansion

rem ---- find the LALA folder (where install was run) ----
set "LALA_DIR="
if exist "%~dp0.venv\Scripts\python.exe" if exist "%~dp0package.json" set "LALA_DIR=%~dp0"
if not defined LALA_DIR (
  for /d %%D in ("%USERPROFILE%\Downloads\LALA-*" "%USERPROFILE%\OneDrive\Desktop\LALA-*" "%USERPROFILE%\Desktop\LALA-*" "%USERPROFILE%\Documents\LALA-*" "%USERPROFILE%\LALA") do (
    if not defined LALA_DIR if exist "%%D\.venv\Scripts\python.exe" if exist "%%D\package.json" set "LALA_DIR=%%D\"
  )
)
if not defined LALA_DIR (
  echo LALA folder not found. Run "install" once first, then double-click me again.
  pause
  exit /b 1
)
cd /d "%LALA_DIR%"

rem ---- start the brain quietly (only if not already running) ----
powershell -NoProfile -Command "try{(New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',8420);exit 0}catch{exit 1}"
if errorlevel 1 (
  start "LALA brain" /min "%LALA_DIR%.venv\Scripts\python.exe" -m assistant --serve
)

rem ---- desktop engine (one-time) + the app window ----
if not exist node_modules (
  echo First run: installing the desktop engine (one-time)...
  call npm install -q --no-audit --no-fund
)
start "LALA desktop" /min cmd /c "npm start"
exit /b 0
