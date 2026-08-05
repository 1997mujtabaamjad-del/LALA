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

    from . import gpu

    device, compute = gpu.stt_plan(
        cfg.get("prefer_gpu", True),
        gpu.cuda_device_count(),
        forced=None if cfg.get("stt_device", "auto") == "auto" else cfg.get("stt_device"),
    )
    if _whisper_model is None or (_whisper_model[0] != (device, compute)):
        _whisper_model = ((device, compute),
                          WhisperModel("base", device=device, compute_type=compute))
    import numpy as np

    segments, _ = _whisper_model[1].transcribe(
        (audio_int16.astype(np.float32) / 32768.0),
        language=cfg.get("stt_language", "en") or None,
        vad_filter=True,
    )
    return " ".join(seg.text for seg in segments).strip()


class StreamingTranscriber:
    """Live partial results while the user speaks (Vosk), best-accuracy final
    (faster-whisper when installed, else the Vosk final). No model downloads —
    live mode is only active when the offline model is already present."""

    def __init__(self, cfg):
        self.cfg = cfg
        self.frames = []
        self.rec = None
        try:
            from vosk import KaldiRecognizer, Model as VoskModel

            from . import wake

            if wake.vosk_model_ready():
                self.rec = KaldiRecognizer(VoskModel(wake.vosk_model_dir()), 16000)
        except Exception:  # noqa: BLE001
            self.rec = None

    @property
    def live(self):
        return self.rec is not None

    def feed(self, pcm):
        """Returns the current partial transcript (may be '')."""
        self.frames.append(pcm)
        if self.rec is None:
            return ""
        finished = self.rec.AcceptWaveForm(pcm.tobytes())
        if finished:
            return self.rec.Result().get("text", "")
        return self.rec.PartialResult().get("partial", "")

    def finish(self):
        """Final transcript for the whole utterance."""
        import numpy as np

        audio = np.concatenate(self.frames) if self.frames else np.zeros(1, dtype=np.int16)
        if local_available():
            try:
                return _local(audio, self.cfg)
            except Exception:  # noqa: BLE001
                pass
        if self.rec is not None:
            return self.rec.FinalResult().get("text", "")
        return ""


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
