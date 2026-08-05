"""
Voice activity detection: Silero (neural) with energy-threshold fallback.

Silero runs from the `silero-vad` package's bundled ONNX model via
onnxruntime — no torch, ~2 MB model, streaming 512-sample windows.
Used by recording endpointing and barge-in; everything degrades to the
classic energy VAD when onnxruntime/silero-vad aren't installed.
"""

import os

import numpy as np

THRESHOLD = 0.5
WINDOW = 512  # silero @16 kHz = 32 ms


def vad_plan(prefer_silero, ort_ok, model_ok):
    """Pure planner (unit-tested)."""
    return "silero" if (prefer_silero and ort_ok and model_ok) else "energy"


class EnergyVAD:
    """Classic RMS threshold — always available."""

    def __init__(self, rms=0.012):
        self.rms = rms

    def prob(self, chunk):
        r = float(np.sqrt(np.mean((chunk.astype(np.float32) / 32768.0) ** 2)))
        return min(1.0, r / (self.rms * 2))

    def speech(self, chunk):
        return self.prob(chunk) >= THRESHOLD

    def reset(self):
        pass


class SileroVAD:
    """Neural speech probability, streamed in 512-sample windows.
    Uses the official silero-vad torch JIT per-chunk API when available
    (the package ships torch); falls back to the bundled ONNX otherwise."""

    def __init__(self):
        self._mode = None
        try:
            from silero_vad import load_silero_vad

            self.model = load_silero_vad()
            self.model.reset_states()
            self._mode = "torch"
        except Exception:  # noqa: BLE001
            try:
                import onnxruntime as ort
                import silero_vad

                path = os.path.join(os.path.dirname(silero_vad.__file__),
                                    "data", "silero_vad.onnx")
                self.sess = ort.InferenceSession(path, providers=["CPUExecutionProvider"])
                self.state = np.zeros((2, 1, 128), dtype=np.float32)
                self._mode = "onnx"
            except Exception:  # noqa: BLE001
                raise
        self._buf = np.zeros(0, dtype=np.float32)

    def reset(self):
        self._buf = np.zeros(0, dtype=np.float32)
        if self._mode == "torch":
            self.model.reset_states()
        else:
            self.state = np.zeros((2, 1, 128), dtype=np.float32)

    def prob(self, chunk):
        x = np.concatenate([self._buf, chunk.astype(np.float32) / 32768.0])
        best = 0.0
        i = 0
        while i + WINDOW <= len(x):
            seg = x[i:i + WINDOW]
            if self._mode == "torch":
                import torch

                with torch.no_grad():
                    best = max(best, float(self.model(torch.from_numpy(seg), 16000)))
            else:
                out, state_n = self.sess.run(
                    None,
                    {"input": seg[None, :], "state": self.state,
                     "sr": np.array(16000, dtype=np.int64)},
                )
                self.state = state_n
                best = max(best, float(np.array(out).ravel()[0]))
            i += WINDOW
        self._buf = x[i:]
        return best

    def speech(self, chunk):
        return self.prob(chunk) > THRESHOLD


def available():
    try:
        import onnxruntime  # noqa: F401
        import silero_vad  # noqa: F401
        return True
    except ImportError:
        return False


def make_vad(cfg):
    plan = vad_plan(cfg.get("prefer_silero", True), available(), True)
    if plan == "silero":
        try:
            return SileroVAD()
        except Exception:  # noqa: BLE001
            pass
    return EnergyVAD()
