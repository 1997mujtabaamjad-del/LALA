"""Settings with sensible defaults, persisted to assistant/data/config.json."""

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")

DEFAULTS = {
    "name": "LALA",
    # Wake word: any phrase — fuzzy-spotted offline by Vosk by default.
    # Zoo words (hey_jarvis, alexa, …) use OpenWakeWord when installed.
    "wake_word": "hey_laala",
    "wake_enabled": True,
    # Keep listening for follow-ups after each reply until you go quiet or
    # say "stop listening".
    "continuous_conversation": True,
    "conversation_window_s": 8,
    # auto = try ollama, then openai, then offline mock
    "llm_provider": "auto",
    "openai_api_key": os.environ.get("OPENAI_API_KEY", ""),
    "openai_model": "gpt-4o-mini",
    "ollama_model": "llama3.1",
    "ollama_url": "http://localhost:11434",
    # auto = faster-whisper if installed else OpenAI API
    "stt_provider": "auto",
    # auto = piper if model present else elevenlabs if key else silent
    "tts_provider": "auto",
    "elevenlabs_api_key": os.environ.get("ELEVENLABS_API_KEY", ""),
    "elevenlabs_voice_id": "21m00Tcm4TlvDq8ikWAM",  # Rachel
    "elevenlabs_model": "eleven_turbo_v2_5",
    "stt_language": "en",
    "memory_window": 12,  # messages kept in LLM context
    # GPU: use CUDA for faster-whisper (fp16) and Piper when available
    "prefer_gpu": True,
    "stt_device": "auto",  # auto | cpu | cuda
    # Smart lights: auto | hue | homeassistant | wled | none
    "lights_provider": "auto",
    "hue_ip": "",
    "hue_key": "",
    "ha_url": "",
    "ha_token": "",
    "wled_ip": "",
}


def config_path():
    return os.path.join(DATA_DIR, "config.json")


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(config_path(), "r", encoding="utf8") as fh:
            cfg.update(json.load(fh))
    except (OSError, ValueError):
        pass
    return cfg


def save(cfg):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(config_path(), "w", encoding="utf8") as fh:
        json.dump(cfg, fh, indent=2)
