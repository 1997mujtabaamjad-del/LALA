@echo off
rem LALA one-click DESKTOP BUILD (Windows)
setlocal enabledelayedexpansion
cd /d "%~dp0\.."

echo ===============================================
echo   LALA desktop build (Windows)
echo ===============================================
where node >nul 2>&1 || (echo ✖ Node 18+ required & pause & exit /b 1)

if not exist node_modules\electron-builder (
  echo → installing build deps …
  call npm install --no-audit --no-fund
)

echo → building Windows installer (NSIS) …
call npx electron-builder --win --publish never
echo → installer in release\

where python >nul 2>&1
if not errorlevel 1 (
  echo → building Python assistant .exe …
  python -m pip install --user -q pyinstaller
  python -m PyInstaller packaging\lala-assistant.spec --noconfirm
  echo → binary in dist\lala-assistant.exe
)

echo ===============================================
echo   ✔ done — install from release\ ^& dist\
echo ===============================================
pause
