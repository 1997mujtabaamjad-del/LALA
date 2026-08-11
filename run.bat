@echo off
title Laalaa J.A.R.V.I.S. AI Assistant
echo ========================================================
echo   Launching Laalaa J.A.R.V.I.S. AI Companion...
echo ========================================================

cd /d C:\Users\mmujt\bishu
call venv\Scripts\activate.bat
set PYTHONPATH=src
python -m bishu

pause
