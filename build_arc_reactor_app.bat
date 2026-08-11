@echo off
title Build Standalone Laalaa Arc Reactor .EXE App
cd /d "%~dp0"

echo ========================================================
echo   Compiling Standalone Laalaa Arc Reactor .EXE App...
echo ========================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [1/3] Installing PyInstaller compiler...
pip install pyinstaller

echo.
echo [2/3] Compiling Laalaa Arc Reactor .EXE Application...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 build_exe.py
) else (
    python build_exe.py
)

echo.
echo [3/3] Opening application folder...
if exist "dist\Laalaa_Arc_Reactor" (
    explorer "dist\Laalaa_Arc_Reactor"
)

echo.
echo ========================================================
echo Standalone .EXE build complete!
pause
