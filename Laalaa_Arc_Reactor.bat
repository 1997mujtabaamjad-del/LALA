@echo off
title Laalaa J.A.R.V.I.S. Arc Reactor AI Companion
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

set PYTHONPATH=src

where py >nul 2>nul
if %errorlevel%==0 (
    set "PY_EXE=py -3"
) else (
    set "PY_EXE=python"
)

%PY_EXE% -m bishu
