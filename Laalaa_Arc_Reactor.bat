@echo off
title Laalaa J.A.R.V.I.S. Arc Reactor AI Companion
cd /d "%~dp0"

echo ========================================================
echo   Launching Laalaa Arc Reactor AI Companion...
echo ========================================================
echo.

if exist "venv\Scripts\python.exe" (
    set "PY_EXE=venv\Scripts\python.exe"
    goto RUN_APP
)

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=py -3"
    goto RUN_APP
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=python"
    goto RUN_APP
)

if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto RUN_APP
)
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PY_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto RUN_APP
)

echo [ERROR] Python 3 was not found on your system!
pause
exit /b 1

:RUN_APP
echo Starting Laalaa Arc Reactor App...
set PYTHONPATH=src
%PY_EXE% -m bishu

echo.
echo Laalaa finished.
pause
