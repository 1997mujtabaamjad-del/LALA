#!/bin/bash
# Master All-In-One Runner for Git Bash

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
fi

echo "[1/3] Syncing latest code from GitHub..."
git fetch origin arena/019fe847-lala &>/dev/null
git checkout -f arena/019fe847-lala &>/dev/null
git pull origin arena/019fe847-lala &>/dev/null

echo "[2/3] Verifying Python environment & launching Laalaa..."
export PYTHONPATH=src

if command -v py &> /dev/null; then
    py -3 -m bishu
elif command -v python3 &> /dev/null; then
    python3 -m bishu
elif command -v python &> /dev/null; then
    python -m bishu
else
    echo "Python 3 not found in PATH! Please install Python 3.11."
fi
