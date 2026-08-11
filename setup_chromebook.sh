#!/bin/bash
# Setup script for running Bishu on Samsung Chromebook 4 (ChromeOS / Crostini Linux container)

set -e

echo "=== Bishu Setup for Samsung Chromebook 4 (Crostini Linux) ==="

echo "[1/4] Installing system dependencies (PyQt5, PortAudio, eSpeak)..."
sudo apt update
sudo apt install -y \
    python3-pyqt5 \
    python3-psutil \
    python3-numpy \
    portaudio19-dev \
    python3-pyaudio \
    espeak \
    libespeak1 \
    libgl1-mesa-glx \
    pulseaudio

echo "[2/4] Installing Python dependencies..."
pip install --break-system-packages pyttsx3 sounddevice ollama || pip install pyttsx3 sounddevice ollama

echo "[3/4] Recommended Ollama model for Chromebook (4GB RAM):"
echo "Run: ollama pull tinyllama  OR  ollama pull qwen2.5:0.5b"

echo "[4/4] ChromeOS Microphone Permission check:"
echo "Note: Make sure microphone access is turned ON in Chrome OS Settings:"
echo "Settings -> Apps -> Linux Development Environment -> Allow Linux to access your microphone."

echo ""
echo "=== Setup complete! Run Bishu with: ==="
echo "PYTHONPATH=src python3 -m bishu.app"
