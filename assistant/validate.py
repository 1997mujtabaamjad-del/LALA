"""
Validate configured API keys locally: `python -m assistant --validate`
Checks Ollama, Deepgram, OpenAI and ElevenLabs without printing secrets.
"""

import io
import wave

import requests

from . import config


def _tiny_wav():
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 1600)  # 0.1 s of silence
    return buf.getvalue()


def check_ollama(cfg):
    try:
        r = requests.get(cfg["ollama_url"] + "/api/tags", timeout=2)
        return r.ok
    except requests.RequestException:
        return False


def check_deepgram(cfg):
    key = cfg.get("deepgram_api_key")
    if not key:
        return None
    try:
        r = requests.post(
            "https://api.deepgram.com/v1/listen",
            params={"model": "nova-2"},
            headers={"Authorization": f"Token {key}", "Content-Type": "audio/wav"},
            data=_tiny_wav(), timeout=15,
        )
        return r.ok
    except requests.RequestException:
        return False


def check_openai(cfg):
    key = cfg.get("openai_api_key")
    if not key:
        return None
    try:
        r = requests.get("https://api.openai.com/v1/models",
                         headers={"Authorization": f"Bearer {key}"}, timeout=15)
        return r.ok
    except requests.RequestException:
        return False


def check_elevenlabs(cfg):
    key = cfg.get("elevenlabs_api_key")
    if not key:
        return None
    try:
        r = requests.get("https://api.elevenlabs.io/v1/user",
                         headers={"xi-api-key": key}, timeout=15)
        return r.ok
    except requests.RequestException:
        return False


def _show(name, result):
    if result is None:
        print(f"  {name:12} — no key configured")
    elif result:
        print(f"  {name:12} ✔ valid")
    else:
        print(f"  {name:12} ✖ rejected / unreachable")


def main():
    cfg = config.load()
    print("\n=== LALA key validation ===")
    _show("ollama", check_ollama(cfg))
    _show("deepgram", check_deepgram(cfg))
    _show("openai", check_openai(cfg))
    _show("elevenlabs", check_elevenlabs(cfg))
    print("\nKeys are read from environment or assistant/.env (gitignored).\n")
