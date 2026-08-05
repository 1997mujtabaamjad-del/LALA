"""
ElevenLabs API helpers: key validation, voice catalogue, synthesis.
Used by tts.py and the --deploy wizard.
"""

import requests

BASE = "https://api.elevenlabs.io/v1"
DEFAULT_MODEL = "eleven_turbo_v2_5"  # lowest latency, great quality
TIMEOUT = 60


def _headers(key):
    return {"xi-api-key": key}


def validate_key(key):
    """True when the API key works. Raises requests.HTTPError on 4xx/5xx."""
    r = requests.get(f"{BASE}/user", headers=_headers(key), timeout=15)
    r.raise_for_status()
    return True


def list_voices(key):
    """[{"voice_id", "name", "category"}] of the account's available voices."""
    r = requests.get(f"{BASE}/voices", headers=_headers(key), timeout=15)
    r.raise_for_status()
    return [
        {"voice_id": v["voice_id"], "name": v.get("name", "?"), "category": v.get("category", "")}
        for v in r.json().get("voices", [])
    ]


def find_voice(key, name_or_id):
    """Resolve a voice by exact name, partial name, or raw id."""
    voices = list_voices(key)
    for v in voices:
        if v["voice_id"] == name_or_id:
            return v
    low = (name_or_id or "").lower()
    for v in voices:
        if low and low in v["name"].lower():
            return v
    return voices[0] if voices else None


def synthesize(key, voice_id, text, model=DEFAULT_MODEL):
    """Returns MP3 bytes."""
    r = requests.post(
        f"{BASE}/text-to-speech/{voice_id}",
        headers=_headers(key),
        json={"text": text, "model_id": model,
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=TIMEOUT,
    )
    r.raise_for_status()
    return r.content
