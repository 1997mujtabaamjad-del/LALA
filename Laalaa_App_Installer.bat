@echo off
title Laalaa AI Windows App Installer
cd /d "%~dp0"

echo ========================================================
echo   Installing Laalaa AI Companion Windows App
echo ========================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    goto INSTALL_APP
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=py -3"
    goto INSTALL_APP
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=python"
    goto INSTALL_APP
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto INSTALL_APP
)

echo [ERROR] Python 3 was not found!
pause
exit /b 1

:INSTALL_APP
echo [1/2] Installing core app dependencies...
%PY_EXE% -m pip install PyQt5 psutil sounddevice numpy plyer ollama pystray pillow SpeechRecognition pyttsx3 pyautogui pywhatkit langgraph openai >nul 2>&1

echo.
echo [2/2] Registering 'Laalaa' Shortcuts on Desktop & Windows Start Menu...
set PYTHONPATH=src
%PY_EXE% -c "from bishu.core.app_packager import AppPackagerEngine; packager = AppPackagerEngine(); print(packager.install_desktop_and_startmenu_shortcuts())"

echo.
echo ========================================================
echo 🎉 Laalaa Windows App Installation Complete!
echo You can now search "Laalaa" in Windows Start Menu or Desktop.
pause
