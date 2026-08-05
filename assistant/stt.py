"""
Speech-to-text: local faster-whisper, Deepgram (streaming-capable), or the
OpenAI Whisper API. `transcribe(int16_audio, cfg)` -> text.
All providers optional at import time.
"""

import io
import json
import threading
import time
import wave

import requests

_whisper_model = None


def local_available():
    import importlib.util

    return importlib.util.find_spec("faster_whisper") is not None


def resolve_provider(cfg):
    pref = cfg.get("stt_provider", "auto")
    if pref in ("local", "openai", "deepgram"):
        return pref
    if local_available():
        return "local"
    if cfg.get("deepgram_api_key"):
        return "deepgram"
    return "openai"


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
    if provider == "deepgram":
        return _deepgram(audio_int16, cfg, rate)
    return _openai(audio_int16, cfg, rate)


# ---------------------------------------------------------------------------
# Deepgram
# ---------------------------------------------------------------------------

def parse_deepgram(payload):
    """Pure parser (unit-tested) for the batch /v1/listen response."""
    try:
        return payload["results"]["channels"][0]["alternatives"][0]["transcript"].strip()
    except (KeyError, IndexError, TypeError):
        return ""


def parse_dg_message(payload):
    """Pure parser (unit-tested) for streaming WS messages: (text, is_final)."""
    try:
        alt = payload["channel"]["alternatives"][0]
        return (alt.get("transcript", "") or "", bool(payload.get("is_final")))
    except (KeyError, IndexError, TypeError):
        return "", False


def _deepgram(audio_int16, cfg, rate):
    if not cfg.get("deepgram_api_key"):
        raise RuntimeError("No Deepgram API key configured.")
    r = requests.post(
        "https://api.deepgram.com/v1/listen",
        params={"model": "nova-2", "smart_format": "true",
                "language": cfg.get("stt_language", "en") or "en"},
        headers={"Authorization": f"Token {cfg['deepgram_api_key']}",
                 "Content-Type": "audio/wav"},
        data=_to_wav_bytes(audio_int16, rate),
        timeout=30,
    )
    r.raise_for_status()
    return parse_deepgram(r.json())


class DeepgramLive:
    """WebSocket streaming partials (needs `pip install websocket-client`)."""

    def __init__(self, key, lang="en"):
        import websocket  # websocket-client

        self.ws = websocket.create_connection(
            "wss://api.deepgram.com/v1/listen?model=nova-2&encoding=linear16"
            f"&sample_rate=16000&channels=1&interim_results=true&language={lang}",
            header=[f"Authorization: Token {key}"],
            timeout=5,
        )
        self.finals = []
        self.interim = ""
        self._thread = threading.Thread(target=self._read, daemon=True)
        self._thread.start()

    def _read(self):
        while True:
            try:
                msg = self.ws.recv()
            except Exception:  # noqa: BLE001 — closed socket ends the loop
                break
            if not msg:
                continue
            try:
                text, is_final = parse_dg_message(json.loads(msg))
            except ValueError:
                continue
            if text:
                if is_final:
                    self.finals.append(text)
                    self.interim = ""
                else:
                    self.interim = text

    def feed(self, pcm):
        self.ws.send_binary(pcm.tobytes())
        return self.partial()

    def partial(self):
        return (" ".join(self.finals) + " " + self.interim).strip()

    def finish(self):
        try:
            self.ws.send('{"type":"CloseStream"}')
        except Exception:  # noqa: BLE001
            pass
        deadline = time.time() + 1.5
        while time.time() < deadline and self._thread.is_alive():
            time.sleep(0.05)
        try:
            self.ws.close()
        except Exception:  # noqa: BLE001
            pass
        return " ".join(self.finals).strip() or self.interim


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
        self.dg = None
        pref = cfg.get("stt_provider", "auto")
        # Live partials: Deepgram (cloud, true streaming) first when keyed,
        # then local Vosk when the offline model is present.
        if pref in ("auto", "deepgram") and cfg.get("deepgram_api_key"):
            try:
                self.dg = DeepgramLive(cfg["deepgram_api_key"],
                                       cfg.get("stt_language", "en") or "en")
            except Exception:  # noqa: BLE001
                self.dg = None
        if self.dg is None:
            try:
                from vosk import KaldiRecognizer, Model as VoskModel

                from . import wake

                if wake.vosk_model_ready():
                    self.rec = KaldiRecognizer(VoskModel(wake.vosk_model_dir()), 16000)
            except Exception:  # noqa: BLE001
                self.rec = None

    @property
    def live(self):
        return self.dg is not None or self.rec is not None

    def feed(self, pcm):
        """Returns the current partial transcript (may be '')."""
        self.frames.append(pcm)
        if self.dg is not None:
            try:
                return self.dg.feed(pcm)
            except Exception:  # noqa: BLE001
                self.dg = None
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
        if self.dg is not None:
            try:
                return self.dg.finish()
            except Exception:  # noqa: BLE001
                pass
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
