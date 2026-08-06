"""
Computer vision layer: desktop capture → OCR → description.
Optional deps: mss (capture), pytesseract + tesseract (OCR).
Webcam/face/gesture are consent-gated stubs until deps + permission exist.
"""

import os
import time

from . import config

OUT = lambda: os.path.join(config.DATA_DIR, "vision")  # noqa: E731


def capture():
    """Screenshot the desktop; returns path or None."""
    try:
        import mss

        os.makedirs(OUT(), exist_ok=True)
        path = os.path.join(OUT(), f"shot-{int(time.time())}.png")
        with mss.mss() as sct:
            sct.shot(output=path)
        return path
    except Exception:  # noqa: BLE001
        return None


def ocr(path):
    try:
        from PIL import Image
        import pytesseract

        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception:  # noqa: BLE001
        return None


def describe():
    path = capture()
    if not path:
        return ("Vision needs a desktop + `pip install mss pytesseract` "
                "(and the tesseract binary).")
    text = ocr(path)
    if text is None:
        return f"Captured {os.path.basename(path)} — OCR unavailable (install pytesseract)."
    return f"I see on screen: {text[:400]}" or "Screen captured, but it looks blank."
