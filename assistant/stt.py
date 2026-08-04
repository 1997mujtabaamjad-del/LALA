"""
Speech-to-text: local faster-whisper, or the OpenAI Whisper API.
`transcribe(int16_audio, cfg)` -> text. Both providers optional at import time.
"""

import io
import wave

import requests

_whisper_model = None


def local_available():
    try:
        import faster_whisper  # noqa: F401
        return True
    except ImportError:
        return False


def resolve_provider(cfg):
    pref = cfg.get("stt_provider", "auto")
    if pref in ("local", "openai"):
        return pref
    return "local" if local_available() else "openai"


def _to_wav_bytes(audio_int16, rate=16000):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()


def transcribe(audio_int16, cfg, rate=16000):
    provider = resolve_provider(cfg)
    if provider == "local":
        return _local(audio_int16, cfg)
    return _openai(audio_int16, cfg, rate)


def _local(audio_int16, cfg):
    global _whisper_model
    from faster_whisper import WhisperModel

    if _whisper_model is None:
        _whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    import numpy as np

    segments, _ = _whisper_model.transcribe(
        (audio_int16.astype(np.float32) / 32768.0),
        language=cfg.get("stt_language", "en") or None,
        vad_filter=True,
    )
    return " ".join(seg.text for seg in segments).strip()


def _openai(audio_int16, cfg, rate):
    if not cfg.get("openai_api_key"):
        raise RuntimeError("No local Whisper and no OpenAI key — STT unavailable.")
    r = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization": f"Bearer {cfg['openai_api_key']}"},
        files={"file": ("audio.wav", _to_wav_bytes(audio_int16, rate), "audio/wav")},
        data={"model": "whisper-1", "language": cfg.get("stt_language", "en") or ""},
        timeout=60,
    )
    r.raise_for_status()
    return r.json().get("text", "").strip()
