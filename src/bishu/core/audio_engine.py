"""Audio engine — deadlock-free, C++ thread-safe microphone listener."""

import collections
import time
import threading
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal

try:
    import sounddevice as sd
    HAS_SD = True
except Exception:
    sd = None
    HAS_SD = False


class AudioEngine(QObject):
    """Monitors microphone input and emits voice_detected signal cleanly from Python thread."""

    voice_detected = pyqtSignal(float)

    def __init__(self, threshold=0.02, sample_rate=16000):
        super().__init__()
        self.threshold = threshold
        self.sample_rate = sample_rate
        self._stream = None
        self._running = False
        self._thread = None
        self._monitor_thread = None
        self.latest_volume = 0.0
        self.buffer = collections.deque(maxlen=12)

    def start(self, callback=None):
        if callback:
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

    def get_buffered_audio(self) -> np.ndarray:
        """Get recorded audio directly from in-memory buffer."""
        if not self.buffer:
            return np.array([], dtype='int16')
        try:
            return np.concatenate(list(self.buffer), axis=0)
        except Exception:
            return np.array([], dtype='int16')

    def _audio_callback(self, indata, frames, time_info, status):
        """C++ PortAudio Callback: ONLY copies numpy audio data into memory buffer."""
        if not self._running:
            return

        try:
            audio_chunk = (indata * 32767).astype(np.int16)
            self.buffer.append(audio_chunk.copy())
            self.latest_volume = float(np.linalg.norm(indata) / np.sqrt(len(indata)))
        except Exception:
            pass

    def _signal_emitter_loop(self):
        """Isolated Python Thread: Safely checks volume and emits Qt signals."""
        last_emit = 0.0
        while self._running:
            time.sleep(0.1)
            vol = self.latest_volume
            now = time.time()
            if vol > self.threshold and (now - last_emit > 2.0):
                last_emit = now
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
