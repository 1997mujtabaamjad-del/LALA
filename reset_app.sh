#!/bin/bash
# Hard reset local repo to match GitHub remote 100%

cd "$(dirname "$0")"

echo "[1/3] Hard resetting local folder to match GitHub origin..."
git fetch origin arena/019fe847-lala
git reset --hard origin/arena/019fe847-lala
git clean -fd

echo "[2/3] Setting PYTHONPATH..."
export PYTHONPATH=src

echo "[3/3] Launching Laalaa..."
if command -v py &> /dev/null; then
    py -3 -m bishu
elif command -v python3 &> /dev/null; then
    python3 -m bishu
elif command -v python &> /dev/null; then
    python -m bishu
fi
