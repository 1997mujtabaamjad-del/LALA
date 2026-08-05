"""
v1.2 — multi-user voice profiles.

Each profile: name, facts (personalization for the LLM), preferred language,
default role, and an optional voiceprint (20-dim log-spectral vector) so LALA
can recognize who is talking and greet them by name.

Data lives in assistant/data/profiles.json. Memory stays household-shared by
design (one assistant for the home); profiles personalize tone & knowledge.
"""

import json
import os

import numpy as np

from . import config

FILE = lambda: os.path.join(config.DATA_DIR, "profiles.json")  # noqa: E731


def load():
    try:
        with open(FILE(), "r", encoding="utf8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {"profiles": {}, "active": ""}


def save(data):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(FILE(), "w", encoding="utf8") as fh:
        json.dump(data, fh, indent=2)


def create(name, facts="", language=None, role=None):
    data = load()
    data["profiles"].setdefault(name, {
        "facts": facts, "language": language, "role": role, "voice": None})
    save(data)
    return data["profiles"][name]


def switch(name):
    data = load()
    if name not in data["profiles"]:
        return False
    data["active"] = name
    save(data)
    return True


def delete(name):
    data = load()
    data["profiles"].pop(name, None)
    if data.get("active") == name:
        data["active"] = ""
    save(data)


def list_names():
    return list(load()["profiles"].keys())


def active():
    data = load()
    name = data.get("active") or ""
    prof = data["profiles"].get(name)
    return {"name": name, **prof} if prof else None


def set_voice(name, vector):
    data = load()
    if name in data["profiles"]:
        data["profiles"][name]["voice"] = [float(v) for v in vector]
        save(data)
        return True
    return False


# ------------------------------------------------------------ voiceprints

def voiceprint(audio_int16, rate=16000, bands=20):
    """Average log-magnitude spectrum over 20 bands — a tiny speaker vector."""
    x = audio_int16.astype(np.float32) / 32768.0
    frame, hop = int(0.025 * rate), int(0.010 * rate)
    if len(x) < frame:
        return np.zeros(bands, dtype=np.float32)
    feats = []
    for i in range(0, len(x) - frame, hop):
        seg = x[i:i + frame] * np.hanning(frame)
        mag = np.abs(np.fft.rfft(seg))[:frame // 2]
        # linear-spaced bands over the first 4 kHz
        maxbin = max(2, int(4000 / (rate / 2) * (frame // 2)))
        edges = np.linspace(1, maxbin, bands + 1).astype(int)
        band = [mag[edges[b]:edges[b + 1]].mean() + 1e-6 for b in range(bands)]
        feats.append(np.log(band))
    v = np.mean(feats, axis=0) if feats else np.zeros(bands)
    v = v - v.mean()
    n = np.linalg.norm(v)
    return (v / n if n else v).astype(np.float32)


def match_voice(audio_int16, max_dist=0.35):
    """Nearest enrolled voiceprint by cosine distance, or None."""
    v = voiceprint(audio_int16)
    best, best_d = None, max_dist
    for name, prof in load()["profiles"].items():
        stored = prof.get("voice")
        if not stored:
            continue
        d = float(np.linalg.norm(v - np.array(stored, dtype=np.float32)))
        if d < best_d:
            best, best_d = name, d
    return best
