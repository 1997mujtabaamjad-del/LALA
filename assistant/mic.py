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
                         min_speech_seconds=0.25):
    """Record from the mic until the user stops talking. Returns int16 array."""
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
            elapsed += (CHUNK / RATE) * 1000
            rms = np.sqrt(np.mean((chunk.astype(np.float32) / 32768.0) ** 2))
            cb_ms = (CHUNK / RATE) * 1000
            if rms > speech_rms:
                speech_ms += cb_ms
                silence_ms = 0
            else:
                silence_ms += cb_ms
            if speech_ms >= min_speech_seconds * 1000 and silence_ms >= silence_seconds * 1000:
                break
    return np.concatenate(frames) if frames else np.zeros(1, dtype=np.int16)


def beep(freq=880, seconds=0.15):
    try:
        import sounddevice as sd

        t = np.linspace(0, seconds, int(RATE * seconds), endpoint=False)
        tone = (0.25 * np.sin(2 * np.pi * freq * t)).astype(np.float32)
        sd.play(tone, RATE)
        sd.wait()
    except Exception:  # noqa: BLE001
        pass
