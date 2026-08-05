"""
Text-to-speech: Piper (local, free) or ElevenLabs (cloud).
`speak(text, cfg)` plays audio when possible and never raises.
"""

import os
import subprocess
import tempfile
import time
import wave

import requests

from . import config

PIPER_MODEL_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/"
    "en/en_US/lessac/medium/en_US-lessac-medium.onnx"
)
PIPER_JSON_URL = PIPER_MODEL_URL + ".json"
PIPER_DIR = os.path.join(config.DATA_DIR, "piper")


def piper_model_paths():
    return (os.path.join(PIPER_DIR, "voice.onnx"), os.path.join(PIPER_DIR, "voice.onnx.json"))


def piper_ready():
    onnx, js = piper_model_paths()
    return os.path.exists(onnx) and os.path.exists(js)


def piper_available():
    import importlib.util

    return importlib.util.find_spec("piper") is not None


def download_piper_voice(progress=None):
    """Fetch the ~60 MB lessac-medium voice. Returns (onnx, json) paths."""
    os.makedirs(PIPER_DIR, exist_ok=True)
    onnx, js = piper_model_paths()
    for url, dest in ((PIPER_MODEL_URL, onnx), (PIPER_JSON_URL, js)):
        if not os.path.exists(dest):
            r = requests.get(url, stream=True, timeout=120)
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            done = 0
            with open(dest, "wb") as fh:
                for chunk in r.iter_content(1 << 16):
                    fh.write(chunk)
                    done += len(chunk)
                    if progress and total:
                        progress(int(done * 100 / total))
    return onnx, js


def resolve_provider(cfg):
    pref = cfg.get("tts_provider", "auto")
    if pref in ("piper", "elevenlabs", "none"):
        return pref
    if piper_available() and piper_ready():
        return "piper"
    if cfg.get("elevenlabs_api_key"):
        return "elevenlabs"
    return "none"


def speak(text, cfg, stop_event=None):
    if not text:
        return
    provider = resolve_provider(cfg)
    try:
        if provider == "piper":
            _speak_piper(text, stop_event)
        elif provider == "elevenlabs":
            _speak_elevenlabs(text, cfg, stop_event)
        # "none": silent mode (e.g. headless / CLI)
    except Exception:  # noqa: BLE001 — never crash the assistant over audio
        pass


def split_sentences(buffer):
    """Split a buffer into complete sentences; returns (sentences, remainder)."""
    import re

    parts = re.split(r"(?<=[.!?])\s+", buffer)
    if len(parts) > 1:
        return parts[:-1], parts[-1]
    return [], buffer


def speak_stream(chunks, cfg, stop_event=None):
    """Speak a streaming reply with minimal latency: the first sentence is
    synthesized while the LLM is still generating the rest. Returns full text.
    A set `stop_event` (barge-in) aborts any remaining sentences."""
    import queue
    import threading

    q = queue.Queue()

    def worker():
        while True:
            item = q.get()
            if item is None:
                return
            if stop_event is not None and stop_event.is_set():
                continue  # drain silently
            speak(item, cfg, stop_event)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    buf = ""
    full = []
    for chunk in chunks:
        if stop_event is not None and stop_event.is_set():
            # Barge-in: cancel the LLM generation itself, not just playback.
            close = getattr(chunks, "close", None)
            if close:
                close()
            break
        buf += chunk
        full.append(chunk)
        sentences, buf = split_sentences(buf)
        for sentence in sentences:
            if sentence.strip():
                q.put(sentence.strip())
    if buf.strip():
        q.put(buf.strip())
    q.put(None)
    thread.join(timeout=180)
    return "".join(full)


def _play_wav(path, stop_event=None):
    try:
        import sounddevice as sd

        with wave.open(path, "rb") as wf:
            frames = wf.readframes(wf.getnframes())
            rate = wf.getframerate()
        import numpy as np

        audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        stream = sd.play(audio, rate)
        while stream.active:
            if stop_event is not None and stop_event.is_set():
                stream.stop()
                return
            time.sleep(0.03)
        return
    except Exception:  # noqa: BLE001
        pass
    proc = None
    for player in ("aplay", "paplay", "afplay"):
        try:
            proc = subprocess.Popen([player, path], stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL)
            break
        except OSError:
            continue
    if proc is None:
        return
    while proc.poll() is None:
        if stop_event is not None and stop_event.is_set():
            proc.kill()
            return
        time.sleep(0.05)


def _speak_piper(text, stop_event=None):
    from piper import PiperVoice

    from . import gpu

    onnx, js = piper_model_paths()
    use_cuda = gpu.tts_plan(True, gpu.onnx_has_cuda())
    try:
        voice = PiperVoice.load(onnx, js, use_cuda=use_cuda)
    except TypeError:  # older piper builds without the use_cuda kwarg
        voice = PiperVoice.load(onnx, js)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        path = tmp.name
    with wave.open(path, "wb") as wf:
        voice.synthesize(text, wf)
    _play_wav(path, stop_event)
    try:
        os.unlink(path)
    except OSError:
        pass


def _speak_elevenlabs(text, cfg, stop_event=None):
    from . import elevenlabs

    if stop_event is not None and stop_event.is_set():
        return
    mp3_bytes = elevenlabs.synthesize(
        cfg["elevenlabs_api_key"],
        cfg["elevenlabs_voice_id"],
        text,
        model=cfg.get("elevenlabs_model", elevenlabs.DEFAULT_MODEL),
    )
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp.write(mp3_bytes)
        mp3 = tmp.name
    played = False
    try:  # decode with ffmpeg when available
        wav = mp3 + ".wav"
        subprocess.run(["ffmpeg", "-y", "-i", mp3, wav], check=True,
                       capture_output=True, timeout=60)
        _play_wav(wav, stop_event)
        played = True
        try:
            os.unlink(wav)
        except OSError:
            pass
    except (OSError, subprocess.SubprocessError):
        pass
    if not played:
        # keep the audio around so it isn't wasted (e.g. headless machines)
        keep = os.path.join(config.DATA_DIR, "last_speech.mp3")
        os.makedirs(config.DATA_DIR, exist_ok=True)
        os.replace(mp3, keep)
        return
    try:
        os.unlink(mp3)
    except OSError:
        pass
