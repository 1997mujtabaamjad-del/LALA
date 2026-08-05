"""
GPU detection & planning.

  - faster-whisper runs on CUDA (float16) when ctranslate2 sees a GPU,
    otherwise CPU (int8).
  - Piper uses onnxruntime's CUDAExecutionProvider when available.
  - Ollama manages its own GPU usage — nothing to do here.

All probes are lazy and failure-tolerant; on machines without a GPU everything
transparently falls back to CPU.
"""

import shutil


def cuda_device_count():
    """Number of CUDA devices visible to ctranslate2 (the faster-whisper runtime)."""
    try:
        import ctranslate2

        return int(ctranslate2.get_cuda_device_count())
    except Exception:  # noqa: BLE001 — ctranslate2 not installed / no CUDA build
        return 0


def onnx_has_cuda():
    """True when onnxruntime offers a CUDA execution provider (for Piper)."""
    try:
        import onnxruntime as ort

        return "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:  # noqa: BLE001
        return False


def nvidia_smi():
    return shutil.which("nvidia-smi") is not None


# ---- pure planners (unit-tested) -------------------------------------------

def stt_plan(prefer_gpu, cuda_count, forced=None):
    """Return (device, compute_type) for faster-whisper."""
    if forced in ("cpu", "cuda"):
        device = forced
    else:
        device = "cuda" if (prefer_gpu and cuda_count > 0) else "cpu"
    compute = "float16" if device == "cuda" else "int8"
    return device, compute


def tts_plan(prefer_gpu, onnx_cuda):
    """Return use_cuda flag for Piper."""
    return bool(prefer_gpu and onnx_cuda)


def summarize():
    return {
        "cuda_devices": cuda_device_count(),
        "onnx_cuda": onnx_has_cuda(),
        "nvidia_smi": nvidia_smi(),
    }
