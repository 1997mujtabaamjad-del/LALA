@echo off
title Hard Reset and Update Laalaa App
cd /d "%~dp0"

echo ========================================================
echo   Hard Resetting Laalaa App to Match Latest GitHub Code
echo ========================================================
echo.

git fetch origin arena/019fe847-lala
git reset --hard origin/arena/019fe847-lala
git clean -fd

echo.
echo ========================================================
echo   Launching Fresh Updated Laalaa AI Companion...
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
