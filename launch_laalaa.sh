#!/bin/bash
# Laalaa Live Local Launcher — Auto-detects python3, python, and py launchers

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
fi

export PYTHONPATH=src

if command -v python3 &> /dev/null; then
    python3 -m bishu
elif command -v python &> /dev/null; then
    python -m bishu
elif command -v py &> /dev/null; then
    py -m bishu
else
    echo "Python not found in PATH! Please install Python 3.11."
fi
