@echo off
rem LALA one-click install (Windows). Double-click me.
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ==============================================
echo   LALA - one-click install
echo ==============================================

where python >nul 2>&1
if errorlevel 1 (
  echo ✖ Python 3.10+ is required - install from python.org first
  pause
  exit /b 1
)

if not exist .venv (
  echo → creating .venv …
  python -m venv .venv
)

echo → installing Python dependencies (STT/TTS/VAD/wake) …
.venv\Scripts\python -m pip install --upgrade pip -q
.venv\Scripts\pip install -q -r assistant\requirements.txt

where npm >nul 2>&1
if not errorlevel 1 (
  echo → installing desktop UI (Electron) …
  call npm install --no-audit --no-fund -q
) else (
  echo → skipping Electron UI (npm not found)
)

rem --- Start Menu + desktop launchers -------------------------------------
set "SM=%APPDATA%\Microsoft\Windows\Start Menu\Programs\LALA"
if not exist "%SM%" mkdir "%SM%"
(
  echo @echo off
  echo cd /d "%cd%"
  echo "%cd%\.venv\Scripts\python" -m assistant %%*
) > "%SM%\LALA.bat"
(
  echo @echo off
  echo cd /d "%cd%"
  echo "%cd%\.venv\Scripts\python" -m assistant %%*
) > "%USERPROFILE%\Desktop\LALA.bat"
echo → Start Menu → LALA → LALA, and Desktop\LALA.bat

echo.
echo ==============================================
echo   ✔ installed
echo      Start Menu → LALA, or: .venv\Scripts\python -m assistant
echo      self-check: .venv\Scripts\python -m assistant --milestone
echo      keys:       .venv\Scripts\python -m assistant --keys
echo ==============================================
set /p MILE="Run the milestone self-check now? [Y/n] "
if /i not "%MILE%"=="n" .venv\Scripts\python -m assistant --milestone
set /p AUTO="Start at login? [y/N] "
if /i "%AUTO%"=="y" .venv\Scripts\python -m assistant --autostart on
echo Enjoy - say "Hey Laala"
pause
