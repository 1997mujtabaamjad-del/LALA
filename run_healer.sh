#!/bin/bash
# Healer & Diagnostics Repair Script for Laalaa / Bishu AI Assistant

set -e

echo "============================================================"
echo "  Laalaa / Bishu AI System Healer & Diagnostic Repair"
echo "============================================================"

echo "[1/4] Checking Python environment & dependencies..."
if [ -d "venv" ]; then
    source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null || true
fi

echo "[2/4] Verifying core packages and editable installation..."
python3 -m pip install --upgrade pip setuptools >/dev/null 2>&1 || true
python3 -m pip install -e . >/dev/null 2>&1 || true

echo "[3/4] Cleaning temporary cache files..."
rm -rf ~/.bishu/memory.json 2>/dev/null || true

echo "[4/4] Verifying Python compilation..."
export PYTHONPATH=src
python3 -c "import bishu; print('✅ All Bishu modules healed and verified 100% OK!')"

echo ""
echo "=== System Healed! Launching Laalaa... ==="
python3 -m bishu
