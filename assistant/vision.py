"""
Computer vision layer.

Inputs (consent-gated, optional deps):
  • desktop capture  — mss
  • webcam           — imagesnap (mac) / fswebcam (linux) / opencv (any)
  • phone camera     — POST /vision/upload to the brain server, then analyze
  • OCR              — pytesseract + tesseract
  • faces            — opencv haar cascade when available
  • object detection / gestures — hooks ready (cv2/mediapipe when installed)

Capabilities: read whiteboards/diagrams (OCR), monitor dashboards (OCR diff),
watch for notification changes.
"""

import glob
import os
import time

from . import config

OUT = lambda: os.path.join(config.DATA_DIR, "vision")  # noqa: E731


def _cv2():
    try:
        import cv2
        return cv2
    except ImportError:
        return None


# ------------------------------------------------------------------ capture
def capture():
    """Desktop screenshot → path or None."""
    try:
        import mss

        os.makedirs(OUT(), exist_ok=True)
        path = os.path.join(OUT(), f"shot-{int(time.time())}.png")
        with mss.mss() as sct:
            sct.shot(output=path)
        return path
    except Exception:  # noqa: BLE001
        return None


def webcam():
    """Webcam frame → path or None (consent = you ran the command)."""
    import subprocess

    os.makedirs(OUT(), exist_ok=True)
    path = os.path.join(OUT(), f"webcam-{int(time.time())}.jpg")
    cv2 = _cv2()
    if cv2:
        cam = cv2.VideoCapture(0)
        ok, frame = cam.read()
        cam.release()
        if ok:
            cv2.imwrite(path, frame)
            return path
        return None
    import sys
    if sys.platform == "darwin":
        try:
            r = subprocess.run(["imagesnap", "-w", "1", path], capture_output=True)
            return path if r.returncode == 0 else None
        except OSError:
            return None
    try:
        r = subprocess.run(["fswebcam", "-q", "--no-banner", path], capture_output=True)
        return path if r.returncode == 0 else None
    except OSError:
        return None


def latest_photo():
    """Most recent phone-uploaded image (POST /vision/upload)."""
    cands = sorted(glob.glob(os.path.join(OUT(), "phone-*")), key=os.path.getmtime)
    return cands[-1] if cands else None


# ------------------------------------------------------------------ analysis
def ocr(path):
    try:
        from PIL import Image
        import pytesseract

        return pytesseract.image_to_string(Image.open(path)).strip()
    except Exception:  # noqa: BLE001
        return None


def faces(path=None):
    """Face count via opencv cascade (permission = explicit command)."""
    path = path or webcam()
    if not path:
        return "No camera available (install opencv-python / imagesnap / fswebcam)."
    cv2 = _cv2()
    if not cv2:
        return f"Captured {os.path.basename(path)} — install opencv-python for face counts."
    try:
        img = cv2.imread(path)
        cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        n = len(cascade.detectMultiScale(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 1.2, 5))
        return f"I see {n} face{'s' if n != 1 else ''} in the frame."
    except Exception as e:  # noqa: BLE001
        return f"Face detection failed: {e}"


def objects(path=None):
    path = path or capture()
    if not path:
        return "Capture unavailable (pip install mss)."
    cv2 = _cv2()
    if not cv2:
        return f"Captured {os.path.basename(path)} — install opencv-python for object detection."
    return "Object detection ready once a DNN model path is set in config['vision_model']."


def describe():
    path = capture()
    if not path:
        return "Vision needs a desktop + `pip install mss pytesseract` (and tesseract)."
    text = ocr(path)
    if text is None:
        return f"Captured {os.path.basename(path)} — OCR unavailable (install pytesseract)."
    return f"I see on screen: {text[:400]}" or "Screen captured, but it looks blank."


def monitor_dashboard(seconds=20):
    """OCR the screen twice, report what changed (dashboards/notifications)."""
    first = ocr(capture()) if capture() else None
    if first is None:
        return "Dashboard watch needs mss + pytesseract."
    time.sleep(min(seconds, 30))
    second = ocr(capture()) or ""
    new = [l for l in second.splitlines() if l not in first.splitlines()]
    gone = [l for l in first.splitlines() if l not in second.splitlines()]
    if not new and not gone:
        return "Watched the dashboard — nothing changed."
    return ("Dashboard changed. New: " + "; ".join(new[:4]) +
            (" | Gone: " + "; ".join(gone[:4]) if gone else ""))
