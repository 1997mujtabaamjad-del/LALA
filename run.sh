#!/bin/bash
# Laalaa Live Local Runner for Git Bash / Terminal

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
    echo "Python 3 not found in PATH! Please install Python 3.11 from python.org."
fi
