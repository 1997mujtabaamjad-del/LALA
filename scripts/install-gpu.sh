#!/bin/bash
# LALA GPU packaging — CUDA-accelerated Whisper + Silero on your machine.
#   bash scripts/install-gpu.sh
set -e
cd "$(dirname "$0")/.."

echo "==============================================="
echo "  LALA GPU setup (CUDA)"
echo "==============================================="
command -v nvidia-smi >/dev/null 2>&1 || { echo "✖ no NVIDIA GPU detected"; exit 1; }
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader

PY="${PY:-.venv/bin/python}"
[ -x "$PY" ] || PY=python3

echo "-> torch (cu121) …"
"$PY" -m pip install -q torch --index-url https://download.pytorch.org/whl/cu121
echo "-> faster-whisper + onnxruntime-gpu …"
"$PY" -m pip install -q faster-whisper onnxruntime-gpu

echo "-> verify …"
"$PY" - <<'EOF'
import ctranslate2, faster_whisper, torch
print("  CUDA devices:", torch.cuda.device_count(), "|", torch.cuda.get_device_name(0))
m = faster_whisper.WhisperModel("base", device="cuda", compute_type="float16")
print("  ✔ Whisper fp16 on GPU ready — LALA will auto-use it (stt_device auto)")
EOF
echo "==============================================="
echo "  ✔ done — run: lala --bench   (watch STT ms drop)"
echo "==============================================="
