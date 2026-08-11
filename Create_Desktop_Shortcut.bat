@echo off
title Create Laalaa Arc Reactor Desktop Shortcut
cd /d "%~dp0"

echo ========================================================
echo   Creating Laalaa Arc Reactor App Shortcut on Desktop...
echo ========================================================

cscript //nologo "%~dp0Create_Desktop_Shortcut.vbs"

echo.
pause
