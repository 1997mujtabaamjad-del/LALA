"""
Wake-word listener — default wake phrase: “Hey Laala”.

Backends, best first:
  - openwakeword      for zoo words (hey_jarvis, alexa, …) or a custom-trained
                      .onnx dropped in assistant/data/models/<wake>_v0.1.onnx
  - vosk              fuzzy keyword spotting for ANY wake phrase (default):
                      streams 16 kHz PCM through a small offline recognizer and
                      matches “hey laala / hey lala / hey la la …” with a regex

`backend_plan()` is pure and unit-tested; `WakeListener` runs the daemon thread.
"""

import os
import re
import threading
import urllib.request
import zipfile

from . import config, mic

THRESHOLD = 0.5
SUPPORTED = ["alexa", "hey_jarvis", "hey_mycroft", "okay_nabu", "tim"]

# Fuzzy wake matcher: tolerates “laala”, “lala”, “la la”, with/without hey/ok.
WAKE_RE = re.compile(r"(?:^|\s)(?:hey|ok|okay|hello|hi)?\s*(?:laala|lala|la\s+la)(?=\s|$)")

VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"
VOSK_MODEL_URL = f"https://alphacephei.com/vosk/models/{VOSK_MODEL_NAME}.zip"


def custom_model_path(wake_word):
    return os.path.join(config.DATA_DIR, "models", f"{wake_word}_v0.1.onnx")


def vosk_model_dir():
    return os.path.join(config.DATA_DIR, "models", VOSK_MODEL_NAME)


def vosk_model_ready():
    return os.path.exists(os.path.join(vosk_model_dir(), "am", "final.mdl"))


def ensure_vosk_model(progress=None):
    """Download + unpack the ~40 MB Vosk model (stdlib only)."""
    if vosk_model_ready():
        return True
    dest = vosk_model_dir()
    os.makedirs(dest, exist_ok=True)
    zip_path = dest + ".zip"
    with urllib.request.urlopen(VOSK_MODEL_URL, timeout=180) as r, open(zip_path, "wb") as fh:
        total = int(r.headers.get("content-length", 0))
        done = 0
        while True:
            chunk = r.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
            done += len(chunk)
            if progress and total:
                progress(int(done * 100 / total))
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(os.path.dirname(dest))
    os.unlink(zip_path)
    return vosk_model_ready()


def has_openwakeword():
    try:
        import openwakeword  # noqa: F401
        return True
    except ImportError:
        return False


def has_vosk():
    try:
        import vosk  # noqa: F401
        return True
    except ImportError:
        return False


def backend_plan(wake_word, has_oww, custom_exists, has_vosk):
    """Pure planner (unit-tested): which backend serves this wake word?"""
    ww = (wake_word or "").strip().lower().replace(" ", "_")
    if has_oww and ww in SUPPORTED:
        return "openwakeword"
    if has_oww and custom_exists:
        return "openwakeword-custom"
    if has_vosk:
        return "vosk"
    return None


class WakeListener:
    def __init__(self, cfg, on_wake, on_status=None):
        self.cfg = cfg
        self.on_wake = on_wake
        self.on_status = on_status
        self._stop = threading.Event()
        self._paused = threading.Event()  # set while the assistant is busy
        self._stream = None

    # ------------------------------------------------------------------ start
    def start(self):
        if not mic.available():
            return False
        wake_word = (self.cfg.get("wake_word") or "hey_laala").lower().replace(" ", "_")
        plan = backend_plan(
            wake_word,
            has_openwakeword(),
            os.path.exists(custom_model_path(wake_word)),
            has_vosk(),
        )
        if plan is None:
            if self.on_status:
                self.on_status("no wake backend (pip install vosk or openwakeword)")
            return False
        if plan.startswith("openwakeword"):
            return self._start_oww(wake_word, plan)
        return self._start_vosk()

    # ------------------------------------------------------- openwakeword path
    def _start_oww(self, wake_word, plan):
        from openwakeword.model import Model

        model_ref = (model_name(wake_word) if plan == "openwakeword"
                     else custom_model_path(wake_word))

        def _run():
            try:
                model = Model(wakeword_models=[model_ref], inference_framework="onnx")
            except Exception:  # noqa: BLE001
                if self.on_status:
                    self.on_status("wake model unavailable")
                return
            if self.on_status:
                self.on_status("armed")
            self._pump(lambda chunk: float(model.predict(chunk)),
                       lambda score: score > THRESHOLD,
                       reset=model.reset)

        return self._spawn(_run)

    # ------------------------------------------------------------- vosk path
    def _start_vosk(self):
        from vosk import KaldiRecognizer, Model as VoskModel

        def _run():
            try:
                ensure_vosk_model(progress=lambda p: self.on_status and
                                  self.on_status(f"model {p}%"))
            except Exception as exc:  # noqa: BLE001
                if self.on_status:
                    self.on_status(f"model download failed: {exc}")
                return
            state = {"rec": None}

            def new_rec():
                state["rec"] = KaldiRecognizer(VoskModel(vosk_model_dir()), 16000)

            new_rec()
            if self.on_status:
                self.on_status("armed (fuzzy vosk)")

            def _check(rec, chunk):
                finished = rec.AcceptWaveForm(chunk.tobytes())
                text = rec.Result() if finished else rec.PartialResult().get("partial", "")
                if WAKE_RE.search((text or "").lower()):
                    new_rec()
                    return 1.0
                return 0.0

            self._pump(lambda chunk: _check(state["rec"], chunk),
                       lambda s: s > 0.5, reset=lambda: None)

        return self._spawn(_run)

    # ---------------------------------------------------------------- plumbing
    def _spawn(self, run):
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return True

    def _pump(self, scorer, triggered, reset):
        import time

        cooldown_until = 0.0

        def _feed(chunk):
            nonlocal cooldown_until
            if self._stop.is_set() or self._paused.is_set():
                return
            if triggered(scorer(chunk)) and time.time() > cooldown_until:
                cooldown_until = time.time() + 2.0
                try:
                    reset()
                except Exception:  # noqa: BLE001
                    pass
                self.on_wake()

        self._stream = mic.open_stream(_feed)
        while not self._stop.wait(0.2):
            pass
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:  # noqa: BLE001
            pass

    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    def stop(self):
        self._stop.set()


def model_name(wake_word):
    ww = (wake_word or "hey_jarvis").strip().lower().replace(" ", "_")
    if ww not in SUPPORTED:
        ww = "hey_jarvis"
    return f"{ww}_v0.1"
