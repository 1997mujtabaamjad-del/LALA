"""Configuration constants for Laalaa AI Assistant."""

# MiniMax AI API Configuration (Optional)
MINIMAX_API_KEY = ""
MINIMAX_GROUP_ID = ""

# Set your preferred Ollama model here: "gemma2:2b", "qwen2.5:0.5b", "deepseek-r1:1.5b", or "llama3.1:latest"
OLLAMA_MODEL = "gemma2:2b"

# Camera Selection Index (0 = Default Webcam, 1 = External USB Camera, 2 = Secondary Camera)
CAMERA_INDEX = 0

# Voice Output Configuration
VOICE_INDEX = 1       # 1 = Female Voice (Microsoft Zira / Female TTS Voice)
VOICE_RATE = 0        # Speech Rate (-10 = Slow, 0 = Normal, +10 = Fast)
VOICE_VOLUME = 100    # Volume Level (0 to 100)
PREFERRED_LANGUAGES = ["en", "hi", "ur"]  # Strictly English, Hindi, and Urdu

SAMPLE_LIMIT = 60
MIN_BASELINE_SAMPLES = 8

CPU_HARD_LIMIT = 95.0
RAM_HARD_LIMIT = 98.0
RAM_CRITICAL_LLM_LIMIT = 85.0  # Strict Cap: Do NOT run local LLM if RAM >= 85%

CPU_SPIKE_DELTA = 30.0
RAM_SPIKE_DELTA = 20.0
MONITOR_INTERVAL_SECONDS = 15   # Sample every 15s
ALERT_COOLDOWN_SECONDS = 300    # 5 minutes cooldown
ALERT_RED_SECONDS = 2
SCHEDULER_INTERVAL_MS = 5000

# Wake-word voice activity threshold (Sensitive threshold for catching quiet speech)
AUDIO_THRESHOLD = 0.005
