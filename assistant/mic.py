"""
Microphone capture with energy-based voice activity detection.
Requires `sounddevice` (pip). All functions return/accept int16 numpy @16 kHz.
"""

import queue

import numpy as np

RATE = 16000
CHUNK = 1280  # 80 ms — the chunk size OpenWakeWord expects


def available():
    try:
        import sounddevice  # noqa: F401
        return True
    except (ImportError, OSError):
        return False


def open_stream(callback):
    """Start a background InputStream; callback receives int16 chunks of CHUNK."""
    import sounddevice as sd

    q = queue.Queue()

    def _cb(indata, frames, time_info, status):
        q.put(indata.copy())

    stream = sd.InputStream(samplerate=RATE, channels=1, dtype="int16",
                            blocksize=CHUNK, callback=_cb)
    stream.start()

    import threading

    def _pump():
        while stream.active:
            try:
                data = q.get(timeout=0.5)
            except queue.Empty:
                continue
            callback(data[:, 0])

    thread = threading.Thread(target=_pump, daemon=True)
    thread.start()
    return stream


def record_until_silence(max_seconds=8.0, speech_rms=0.012, silence_seconds=1.0,
                         min_speech_seconds=0.25, require_speech=False,
                         on_chunk=None, vad=None):
    """Record from the mic until the user stops talking. Returns int16 array,
    or None when `require_speech` is set and no real speech was detected.
    `on_chunk(chunk_int16)` is called live for streaming consumers.
    `vad` (SileroVAD/EnergyVAD) upgrades speech detection from RMS to neural."""
    import sounddevice as sd

    frames = []
    speech_ms = 0
    silence_ms = 0
    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=CHUNK) as stream:
        deadline = max_seconds * 1000
        elapsed = 0
        while elapsed < deadline:
            data, _ = stream.read(CHUNK)
            chunk = data[:, 0]
            frames.append(chunk)
            if on_chunk is not None:
                try:
                    on_chunk(chunk)
                except Exception:  # noqa: BLE001 — never break capture
                    pass
            elapsed += (CHUNK / RATE) * 1000
            is_speech = vad.speech(chunk) if vad is not None else (
                np.sqrt(np.mean((chunk.astype(np.float32) / 32768.0) ** 2)) > speech_rms)
            cb_ms = (CHUNK / RATE) * 1000
            if is_speech:
                speech_ms += cb_ms
                silence_ms = 0
            else:
                silence_ms += cb_ms
            if speech_ms >= min_speech_seconds * 1000 and silence_ms >= silence_seconds * 1000:
                break
    if require_speech and speech_ms < min_speech_seconds * 1000:
        return None
    return np.concatenate(frames) if frames else np.zeros(1, dtype=np.int16)


def save_wav(path, audio_int16, rate=RATE):
    """Persist int16 mono audio as a .wav file. Returns the path."""
    import os
    import wave

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(audio_int16.tobytes())
    return path


def beep(freq=880, seconds=0.15):
    try:
        import sounddevice as sd

        t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
        tone = (0.25 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        sd.play(tone, RATE)
        sd.wait()
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Barge-in: detect that the *user* started talking while LALA is speaking.
# ---------------------------------------------------------------------------

BARGE_RMS = 0.05      # louder than normal VAD — must beat speaker bleed
BARGE_SUSTAIN_MS = 250
BARGE_GRACE_MS = 400  # ignore the first moments of each utterance


def _barge_flags(flags, cb_ms, sustain_ms=BARGE_SUSTAIN_MS, grace_ms=BARGE_GRACE_MS):
    """Pure decider over boolean speech flags (unit-tested)."""
    elapsed = 0
    sustained = 0
    for flag in flags:
        elapsed += cb_ms
        if elapsed < grace_ms:
            continue
        if flag:
            sustained += cb_ms
            if sustained >= sustain_ms:
                return True
        else:
            sustained = 0
    return False


def barge_triggered(rms_values, cb_ms, threshold=BARGE_RMS,
                    sustain_ms=BARGE_SUSTAIN_MS, grace_ms=BARGE_GRACE_MS):
    """Pure decider (unit-tested): would this RMS sequence fire a barge-in?"""
    elapsed = 0
    sustained = 0
    for rms in rms_values:
        elapsed += cb_ms
        if elapsed < grace_ms:
            continue
        if rms > threshold:
            sustained += cb_ms
            if sustained >= sustain_ms:
                return True
        else:
            sustained = 0
    return False


class BargeMonitor:
    """Watches the mic during TTS playback; sets `stop_event` on user speech.
    Uses Silero when provided, else an RMS threshold louder than speaker bleed."""

    def __init__(self, stop_event, cb_ms=80, vad=None):
        self.stop_event = stop_event
        self.cb_ms = cb_ms
        self.vad = vad
        self.barged = False
        self._stream = None
        self._history = []

    def start(self):
        def _feed(chunk):
            if self.vad is not None:
                flag = self.vad.speech(chunk)
                self._history.append(1.0 if flag else 0.0)
                triggered = _barge_flags(self._history, self.cb_ms)
            else:
                rms = float(np.sqrt(np.mean((chunk.astype(np.float32) / 32768.0) ** 2)))
                self._history.append(rms)
                triggered = barge_triggered(self._history, self.cb_ms)
            if not self.barged and triggered:
                self.barged = True
                self.stop_event.set()

        try:
            self._stream = open_stream(_feed)
        except Exception:  # noqa: BLE001
            self._stream = None

    def stop(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass
            self._stream = None
