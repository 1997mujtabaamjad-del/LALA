"""
Scaffold for training a custom "Hey LALA" OpenWakeWord model.

OpenWakeWord ships frozen models (hey_jarvis, alexa, …). Training a new one
needs the upstream training repo + tensorflow; this script handles the parts
we can own here:

  --record N     record N positive samples of you saying "hey lala"
                 (1.2 s each, 16 kHz) into assistant/data/wake_samples/positive/
  --train        print the exact upstream commands to train with your samples

Usage:
  python -m assistant.train_wakeword --record 50
  python -m assistant.train_wakeword --train
"""

import argparse
import os

import numpy as np

from . import config, mic

SAMPLE_DIR = os.path.join(config.DATA_DIR, "wake_samples", "positive")


def record_samples(count):
    os.makedirs(SAMPLE_DIR, exist_ok=True)
    if not mic.available():
        print("Microphone unavailable (pip install sounddevice).")
        return
    existing = len([f for f in os.listdir(SAMPLE_DIR) if f.endswith(".npy")])
    print(f"Say “hey lala” {count} times — press Enter before each take.")
    for i in range(count):
        input(f"  take {existing + i + 1}/{existing + count}…")
        audio = mic.record_until_silence(max_seconds=1.6, silence_seconds=0.35,
                                         min_speech_seconds=0.1)
        path = os.path.join(SAMPLE_DIR, f"positive_{existing + i:04d}.npy")
        np.save(path, audio)
        print(f"    saved {os.path.basename(path)} ({len(audio)} samples)")
    print(f"\n{len(os.listdir(SAMPLE_DIR))} positive samples in {SAMPLE_DIR}")


TRAIN_GUIDE = """
Training “hey lala” (upstream OpenWakeWord pipeline):

  1. git clone https://github.com/dscripka/openWakeWord && cd openWakeWord
  2. pip install -r requirements.txt   # tensorflow, piper synthesis deps…
  3. Add your positives: copy {samples}/*.npy (16 kHz int16) into
     the repo's training positives folder, or list them in a manifest.
  4. Negative speech is synthesized automatically by their pipeline.
  5. Train:
       python -m openwakeword.train --model_name hey_lala \\
              --training_data_dir <your manifest dir> --steps 5000
  6. Export ONNX, then point LALA at it:
       config["wake_word"] = "hey_lala"  (wake.py loads <name>_v0.1.onnx
       from the openWakeWord model dir — drop the file there).

Tip: 200–500 varied positives (you, friends, distances) give a usable model.
""".strip()


def main():
    parser = argparse.ArgumentParser(prog="train_wakeword")
    parser.add_argument("--record", type=int, metavar="N", help="record N positive samples")
    parser.add_argument("--train", action="store_true", help="show upstream training steps")
    args = parser.parse_args()

    if args.record:
        record_samples(args.record)
    if args.train or not args.record:
        print(TRAIN_GUIDE.format(samples=SAMPLE_DIR))


if __name__ == "__main__":
    main()
