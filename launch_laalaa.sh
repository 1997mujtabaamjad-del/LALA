#!/bin/bash
# Laalaa Live Local Launcher — Runs code directly from local src without git pull

cd "$(dirname "$0")"

if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
fi

export PYTHONPATH=src
python3 -m bishu
