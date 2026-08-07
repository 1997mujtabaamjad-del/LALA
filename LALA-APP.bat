@echo off
rem ============================================================
rem  LALA Desktop App - double-click me from ANYWHERE.
rem  Finds your LALA folder by itself, starts the brain quietly,
rem  and opens the real desktop window with the brain logo.
rem ============================================================
setlocal enabledelayedexpansion

rem ---- find the LALA folder: same place as me, or search for lala.bat ----
set "LALA_DIR="
if exist "%~dp0.venv\Scripts\python.exe" if exist "%~dp0package.json" set "LALA_DIR=%~dp0"
if not defined LALA_DIR (
  for /f "delims=" %%F in ('dir /s /b "%USERPROFILE%\Downloads\lala.bat" "%USERPROFILE%\OneDrive\Desktop\lala.bat" "%USERPROFILE%\Desktop\lala.bat" "%USERPROFILE%\Documents\lala.bat" "%USERPROFILE%\lala.bat" 2^>nul') do (
    if not defined LALA_DIR set "LALA_DIR=%%~dpF"
  )
)
if not defined LALA_DIR (
  echo LALA folder not found. Double-click "install" once first, then me.
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
