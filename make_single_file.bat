@echo off
title Build One Single File Laalaa.exe App
cd /d "%~dp0"

echo ========================================================
echo   Building ONE SINGLE FILE: Laalaa.exe
echo ========================================================
echo.

if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

echo [1/2] Installing PyInstaller compiler...
pip install pyinstaller >nul 2>&1

echo [2/2] Compiling into ONE SINGLE FILE (Laalaa.exe)...
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 build_single_exe.py
) else (
    python build_single_exe.py
)

echo.
echo ========================================================
echo SUCCESS! Look in dist folder for Laalaa.exe (1 Single File)
if exist "dist\Laalaa.exe" (
    explorer "dist"
)
pause
