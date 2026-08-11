@echo off
title Launch Laalaa AI Assistant
cd /d "%~dp0"

echo ========================================================
echo   Launching Laalaa AI Voice Companion (Live Code)
echo ========================================================
echo.

rem 1. Check virtual environment
if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    goto RUN_APP
)

rem 2. Check py launcher
where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=py -3"
    goto RUN_APP
)

rem 3. Check python in PATH
where python >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=python"
    goto RUN_APP
)

rem 4. Check standard AppData Python installations
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto RUN_APP
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto RUN_APP
)
if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python310\python.exe"
    goto RUN_APP
)

echo [ERROR] Python 3 was not found in your Windows PATH!
echo Please download Python 3.11 from https://www.python.org/downloads/
echo IMPORTANT: Check the box "Add Python to PATH" during installation.
echo.
pause
exit /b 1

:RUN_APP
echo Using Python runner: %PY_EXE%
set PYTHONPATH=src
%PY_EXE% -m bishu

echo.
echo ========================================================
echo Laalaa application finished.
pause
