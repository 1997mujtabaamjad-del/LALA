"""Audio engine — deadlock-free, high-sensitivity C++ thread-safe microphone listener with automatic gain boosting."""

import collections
import time
import threading

try:
    import numpy as np
    HAS_NUMPY = True
except Exception:
    np = None
    HAS_NUMPY = False

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_QT = True
except Exception:
    QObject = object
    pyqtSignal = lambda *args: None
    HAS_QT = False

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    sd = None
    HAS_SD = False


class AudioEngine(QObject):
    """Monitors microphone input with ultra-sensitive voice activity detection & peak audio gain normalization."""

    voice_detected = pyqtSignal(float) if HAS_QT else None

    def __init__(self, threshold=0.005, sample_rate=16000):
        if HAS_QT:
            super().__init__()
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._stream = None
        self._running = False
        self._thread = None
        self._monitor_thread = None
        self.latest_volume = 0.0
        self._lock = threading.Lock()
        # Increased deque capacity to 30 chunks (7.5 seconds of audio memory)
        self.buffer = collections.deque(maxlen=30)

    def start(self, callback=None):
        if callback and self.voice_detected:
            try:
                self.voice_detected.connect(callback)
            except Exception:
                pass
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._listen_loop,
            daemon=True,
        )
        self._thread.start()

        # Start isolated Python thread for emitting signals (safe from PortAudio C++ callback)
        self._monitor_thread = threading.Thread(
            target=self._signal_emitter_loop,
            daemon=True,
        )
        self._monitor_thread.start()

    def stop(self):
        self._running = False
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

    def get_buffered_audio(self):
        """Get recorded audio directly from in-memory buffer with automatic gain boost for quiet speech."""
        if not HAS_NUMPY or np is None:
            return []

        with self._lock:
            if not self.buffer:
                return np.array([], dtype='int16')
            try:
                buffer_copy = list(self.buffer)
                if not buffer_copy:
                    return np.array([], dtype='int16')
                raw_audio = np.concatenate(buffer_copy, axis=0)
                if len(raw_audio) == 0:
                    return raw_audio

                # Automatic Peak Gain Normalization (Boosts low-volume/quiet speech up to 80% peak scale)
                max_val = np.max(np.abs(raw_audio))
                if 50 < max_val < 22000:
                    scale_factor = 25000.0 / max_val
                    boosted_audio = np.clip(raw_audio * scale_factor, -32768, 32767).astype(np.int16)
                    return boosted_audio

                return raw_audio
            except Exception:
                return np.array([], dtype='int16')

    def _audio_callback(self, indata, frames, time_info, status):
        """C++ PortAudio Callback: ONLY copies numpy audio data into memory buffer."""
        if not self._running or not HAS_NUMPY or np is None:
            return

        try:
            audio_chunk = (indata * 32767).astype(np.int16)
            with self._lock:
                self.buffer.append(audio_chunk.copy())
            self.latest_volume = float(np.linalg.norm(indata) / np.sqrt(len(indata)))
        except Exception:
            pass

    def _signal_emitter_loop(self):
        """Isolated Python Thread: Safely checks volume and emits Qt signals."""
        last_emit = 0.0
        while self._running:
            time.sleep(0.08)
            vol = self.latest_volume
            now = time.time()
            if vol > self.threshold and (now - last_emit > 2.0):
                last_emit = now
                if self.voice_detected:
                    try:
                        self.voice_detected.emit(vol)
                    except Exception:
                        pass

    def _listen_loop(self):
        if not HAS_SD or sd is None:
            print("[AudioEngine] sounddevice unavailable. Audio monitoring in fallback mode.")
            while self._running:
                time.sleep(0.5)
            return

        while self._running:
            try:
                self._stream = sd.InputStream(
                    callback=self._audio_callback,
                    channels=1,
                    samplerate=self.sample_rate,
                    blocksize=4000,
                )
                self._stream.start()

                while self._running:
                    time.sleep(0.2)

            except Exception as e:
                print("[AudioEngine] Resilient stream recovery:", e)
                time.sleep(1.0)

            finally:
                if self._stream:
                    try:
                        self._stream.stop()
                        self._stream.close()
                    except Exception:
                        pass
                    self._stream = None
