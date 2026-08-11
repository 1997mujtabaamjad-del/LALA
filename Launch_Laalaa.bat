@echo off
title Launch Laalaa AI Assistant
cd /d "%~dp0"

echo ========================================================
echo   Launching Laalaa AI Voice Companion (Live Local Code)
echo ========================================================

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

set PYTHONPATH=src
python -m bishu

pause
