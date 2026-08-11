@echo off
title Build Standalone Laalaa Arc Reactor .EXE App
cd /d "%~dp0"

echo ========================================================
echo   Compiling Standalone Laalaa Arc Reactor .EXE App...
echo ========================================================

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

pip install pyinstaller >nul 2>&1

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 build_exe.py
) else (
    python build_exe.py
)

echo.
pause
