@echo off
title Launch Laalaa AI Assistant
cd /d "%~dp0"

echo ========================================================
echo   Launching Laalaa AI Voice Companion (Live Code)
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
