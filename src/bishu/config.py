"""Configuration constants for Laalaa AI Assistant."""

# ElevenLabs AI Voice Configuration (Leo Voice)
ELEVENLABS_API_KEY = ""
ELEVENLABS_VOICE_ID = "d0grukerEzs069eKIauC"    # ElevenLabs Leo Voice ID
ELEVENLABS_MODEL_ID = "eleven_multilingual_v2"  # Multilingual v2 for English, Hindi, Urdu

# NVIDIA Nemotron-3 Ultra 550B AI API Configuration (NVIDIA NIM API build.nvidia.com)
NVIDIA_API_KEY = ""
NVIDIA_MODEL = "nvidia/nemotron-3-ultra-550b-a55b"
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# MiniMax AI API Configuration (Optional)
MINIMAX_API_KEY = ""
MINIMAX_GROUP_ID = ""

# Telegram Bot Mobile Integration (Optional — set token to control Laalaa from your phone)
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Set your preferred Ollama model here: "nemotron-3-ultra", "gemma2:2b", "qwen2.5:0.5b", "deepseek-r1:1.5b", or "llama3.1:latest"
OLLAMA_MODEL = "gemma2:2b"

# Camera Selection Index (0 = Default Webcam, 1 = External USB Camera, 2 = Secondary Camera)
CAMERA_INDEX = 0

# Voice Output Configuration (Crystal-clear accent & relaxed conversational rate)
VOICE_INDEX = 1       # 1 = Female Voice (Microsoft Zira / Female TTS Voice)
VOICE_RATE = -1       # Speech Rate (-1 = Slightly relaxed pace for crystal-clear accent & speech clarity)
VOICE_VOLUME = 100    # Volume Level (0 to 100)
PREFERRED_LANGUAGES = ["en", "hi", "ur"]  # Strictly English, Hindi, and Urdu

SAMPLE_LIMIT = 60
MIN_BASELINE_SAMPLES = 8

CPU_HARD_LIMIT = 99.0          # Only trigger alert if CPU is sustained at 99%+
RAM_HARD_LIMIT = 98.0
RAM_CRITICAL_LLM_LIMIT = 85.0  # Strict Cap: Do NOT run local LLM if RAM >= 85%
CPU_CRITICAL_LLM_LIMIT = 90.0  # Strict Cap: Do NOT run heavy local LLM if CPU >= 90%

CPU_SPIKE_DELTA = 40.0
RAM_SPIKE_DELTA = 25.0
MONITOR_INTERVAL_SECONDS = 30   # Sample every 30s
ALERT_COOLDOWN_SECONDS = 600    # 10 minutes cooldown between alerts
ALERT_RED_SECONDS = 1
SCHEDULER_INTERVAL_MS = 5000

# Wake-word voice activity threshold (Sensitive threshold for catching quiet speech)
AUDIO_THRESHOLD = 0.005
