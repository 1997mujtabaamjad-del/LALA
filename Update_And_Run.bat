@echo off
title Update and Run Laalaa AI Assistant
cd /d "%~dp0"

echo ========================================================
echo   Updating Laalaa to Latest Version from GitHub...
echo ========================================================

git fetch origin arena/019fe847-lala
git checkout arena/019fe847-lala
git pull origin arena/019fe847-lala

echo.
echo ========================================================
echo   Launching Laalaa AI Companion...
echo ========================================================

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

set PYTHONPATH=src

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -m bishu
) else (
    python -m bishu
)

pause
