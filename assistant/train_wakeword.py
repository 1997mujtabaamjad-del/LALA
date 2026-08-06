"""
Custom “Hey Laala” wake-word pipeline.

  python -m assistant.train_wakeword --synthesize 40   # build a dataset with Piper
  python -m assistant.train_wakeword --record 20       # add REAL positives via mic
  python -m assistant.train_wakeword --train           # train if TF is available,
                                                       # else print exact steps

Synthesis varies phrase, punctuation and amplitude so the model generalizes.
"""

import argparse
import os
import random
import wave

import numpy as np

from . import config, mic

OUT = lambda: os.path.join(config.DATA_DIR, "wake_train")  # noqa: E731

POS_PHRASES = ["hey laala", "hey laala,", "hey, laala", "hey lala", "laala",
               "ok laala", "hey laala please"]
NEG_PHRASES = ["hello there", "open youtube", "what time is it", "la la land",
               "how are you", "play some music", "lala is great today",
               "tell me a joke", "hey assistant"]


def _save_wav(path, pcm):
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(pcm.astype(np.int16).tobytes())


def synthesize_dataset(n=40):
    """Generate positives/negatives with the local Piper voice (no network)."""
    try:
        from piper import PiperVoice
    except ImportError:
        print("✖ pip install piper-tts  (then re-run)")
        return None
    from . import tts

    if not tts.piper_ready():
        print("→ downloading Piper voice (~60 MB) …")
        tts.download_piper_voice()
    onnx, js = tts.piper_model_paths()
    voice = PiperVoice.load(onnx, js)

    out = OUT()
    os.makedirs(out, exist_ok=True)
    rng = random.Random(7)
    made = {"pos": 0, "neg": 0}
    for i in range(n):
        phrase = rng.choice(POS_PHRASES)
        path = os.path.join(out, f"pos_{i:03d}.wav")
        with wave.open(path, "wb") as wf:
            voice.synthesize(phrase, wf)
        # amplitude jitter for robustness
        with wave.open(path, "rb") as wf:
            pcm = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16)
        _save_wav(path, pcm * rng.uniform(0.7, 1.0))
        made["pos"] += 1
    for i in range(max(10, n // 2)):
        phrase = rng.choice(NEG_PHRASES)
        path = os.path.join(out, f"neg_{i:03d}.wav")
        with wave.open(path, "wb") as wf:
            voice.synthesize(phrase, wf)
        made["neg"] += 1
    print(f"✔ dataset at {out}: {made['pos']} positives, {made['neg']} negatives")
    return out


def record_positives(count):
    out = os.path.join(OUT(), "real")
    os.makedirs(out, exist_ok=True)
    if not mic.available():
        print("✖ no microphone here")
        return
    existing = len([f for f in os.listdir(out) if f.endswith(".wav")])
    print(f"Say “hey laala” {count} times — Enter before each take.")
    for i in range(count):
        input(f"  take {existing + i + 1}…")
        audio = mic.record_until_silence(max_seconds=1.6, silence_seconds=0.35,
                                         min_speech_seconds=0.1)
        _save_wav(os.path.join(out, f"real_{existing + i:03d}.wav"),
                  audio.astype(np.float32) / 32768.0)
    print(f"✔ {count} real positives saved")


def train():
    out = OUT()
    if not os.path.isdir(out) or not os.listdir(out):
        print("→ no dataset yet; run --synthesize 40 (and --record 20) first")
        return
    have_tf = False
    try:
        import tensorflow  # noqa: F401
        have_tf = True
    except ImportError:
        pass
    if not have_tf:
        print("Dataset ready. To train the ONNX model:")
        print("  1) pip install tensorflow openwakeword")
        print("  2) git clone https://github.com/dscripka/openWakeWord")
        print(f"  3) point its training manifest at {out}")
        print("  4) python -m openwakeword.train --model_name hey_laala --steps 5000")
        print("  5) drop hey_laala.onnx into assistant/data/models/ — LALA picks it up")
        return
    print("→ TensorFlow found: follow openWakeWord's colab with dataset at", out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthesize", type=int, metavar="N")
    ap.add_argument("--record", type=int, metavar="N")
    ap.add_argument("--train", action="store_true")
    a = ap.parse_args()
    if a.synthesize:
        synthesize_dataset(a.synthesize)
    if a.record:
        record_positives(a.record)
    if a.train or not (a.synthesize or a.record):
        train()


if __name__ == "__main__":
    main()
