@echo off
title Laalaa AI System Repair & Diagnostics
cd /d "%~dp0"

echo ========================================================
echo   Laalaa AI System Self-Healing & Diagnostics
echo ========================================================
echo.

rem 1. Check Python installation
where py >nul 2>nul
if %errorlevel%==0 (
    set PY_CMD=py -3
) else (
    where python >nul 2>nul
    if %errorlevel%==0 (
        set PY_CMD=python
    ) else (
        echo [ERROR] Python 3 was not found on your system!
        echo Please download and install Python 3.11 from https://www.python.org/downloads/
        echo Make sure to check "Add Python to PATH" during installation.
        pause
        exit /b 1
    )
)

echo [1/4] Found Python runner: %PY_CMD%
%PY_CMD% --version

echo.
echo [2/4] Installing / Repairing required Python dependencies...
%PY_CMD% -m pip install PyQt5 psutil sounddevice numpy plyer ollama pystray pillow SpeechRecognition pyttsx3 pyautogui pywhatkit langgraph openai

echo.
echo [3/4] Pulling latest Laalaa engine updates from GitHub...
git fetch origin arena/019fe847-lala >nul 2>&1
git checkout arena/019fe847-lala >nul 2>&1
git pull origin arena/019fe847-lala >nul 2>&1

echo.
echo [4/4] Launching Laalaa AI Voice Companion...
echo ========================================================
set PYTHONPATH=src
%PY_CMD% -m bishu

echo.
echo ========================================================
echo Laalaa process finished.
pause
