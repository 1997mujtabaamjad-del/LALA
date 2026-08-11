@echo off
title Laalaa J.A.R.V.I.S. Arc Reactor AI Companion
cd /d "%~dp0"

echo ========================================================
echo   Laalaa J.A.R.V.I.S. Arc Reactor AI Companion
echo ========================================================
echo.

rem 1. Auto-detect Python runner
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    goto START_LAALAA
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=py -3"
    goto START_LAALAA
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=python"
    goto START_LAALAA
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto START_LAALAA
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto START_LAALAA
)

echo [ERROR] Python 3 was not found in your Windows PATH!
echo Please install Python 3.11 from https://www.python.org/downloads/
echo Make sure to check "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:START_LAALAA
echo [1/3] Fetching latest code updates from GitHub...
git fetch origin arena/019fe847-lala >nul 2>&1
git checkout -f arena/019fe847-lala >nul 2>&1
git pull origin arena/019fe847-lala >nul 2>&1

echo [2/3] Verifying required Python dependencies...
%PY_EXE% -m pip install PyQt5 psutil sounddevice numpy plyer ollama pystray pillow SpeechRecognition pyttsx3 pyautogui pywhatkit langgraph openai >nul 2>&1

echo [3/3] Launching Laalaa Arc Reactor App on Screen...
echo.
set PYTHONPATH=src
%PY_EXE% -m bishu

echo.
echo ========================================================
echo Laalaa application finished.
pause
