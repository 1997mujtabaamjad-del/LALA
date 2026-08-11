@echo off
echo ========================================================
echo   Setting up Laalaa / Bishu AI Assistant (Python 3.11)
echo ========================================================

:: Create virtual environment with Python 3.11
python -m venv venv

:: Activate virtual environment
call venv\Scripts\activate.bat

:: Upgrade pip
python -m pip install --upgrade pip setuptools

:: Install all dependencies
pip install PyQt5 psutil pystray pillow plyer ollama sounddevice numpy pyttsx3 SpeechRecognition pyautogui pywhatkit ultralytics opencv-python openai-whisper

:: Install bishu in editable mode
pip install -e .

echo ========================================================
echo   Setup Complete! Launching Laalaa / Bishu...
echo ========================================================
python -m bishu
pause
