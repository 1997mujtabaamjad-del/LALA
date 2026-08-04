"""
Wake-word listener built on OpenWakeWord ("Hey Jarvis" by default).
Runs a daemon thread that feeds 16 kHz int16 chunks to the model and fires
`on_wake()` when the score crosses the threshold.
"""

import threading

from . import mic

THRESHOLD = 0.5

SUPPORTED = ["alexa", "hey_jarvis", "hey_mycroft", "okay_nabu", "tim"]


def model_name(wake_word):
    ww = (wake_word or "hey_jarvis").strip().lower().replace(" ", "_")
    if ww not in SUPPORTED:
        ww = "hey_jarvis"
    return f"{ww}_v0.1"


class WakeListener:
    def __init__(self, cfg, on_wake, on_status=None):
        self.cfg = cfg
        self.on_wake = on_wake
        self.on_status = on_status
        self._stop = threading.Event()
        self._thread = None
        self._stream = None
        self._paused = threading.Event()  # set while the assistant is busy

    def start(self):
        if not mic.available():
            return False
        try:
            from openwakeword.model import Model
        except ImportError:
            return False

        def _run():
            try:
                model = Model(wakeword_models=[model_name(self.cfg["wake_word"])],
                              inference_framework="onnx")
            except Exception:  # noqa: BLE001 (model download failure, etc.)
                if self.on_status:
                    self.on_status("wake model unavailable")
                return

            if self.on_status:
                self.on_status("armed")

            cooldown_until = 0.0
            import time

            def _feed(chunk):
                nonlocal cooldown_until
                if self._stop.is_set():
                    return
                if self._paused.is_set():
                    return
                score = float(model.predict(chunk))
                if score > THRESHOLD and time.time() > cooldown_until:
                    cooldown_until = time.time() + 2.0
                    model.reset()
                    self.on_wake()

            self._stream = mic.open_stream(_feed)
            while not self._stop.wait(0.2):
                pass
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:  # noqa: BLE001
                pass

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        return True

    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    def stop(self):
        self._stop.set()
