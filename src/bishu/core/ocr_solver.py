"""Screen Text Reader (OCR) & Assignment Question Solver Agent."""

import os
import time
from pathlib import Path

try:
    import pyautogui
    from PIL import Image
    HAS_SCREEN_CAPTURE = True
except Exception:
    pyautogui = None
    Image = None
    HAS_SCREEN_CAPTURE = False

try:
    import pytesseract
    HAS_TESSERACT = True
except Exception:
    pytesseract = None
    HAS_TESSERACT = False


class ScreenOCRSolver:
    """Screen Text Reader & AI Assignment Question Solver."""

    def __init__(self, ai_engine=None):
        self.ai = ai_engine
        self.shots_dir = Path.home() / ".bishu" / "ocr_snapshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)

    def capture_screen_text(self) -> str:
        """Capture screen snapshot and extract text via OCR."""
        if not HAS_SCREEN_CAPTURE or not pyautogui:
            return "Screen capture libraries (pyautogui / Pillow) not available."

        try:
            screenshot_path = self.shots_dir / f"ocr_snap_{int(time.time())}.png"
            shot = pyautogui.screenshot()
            shot.save(str(screenshot_path))

            if HAS_TESSERACT and pytesseract:
                img = Image.open(screenshot_path)
                ocr_text = pytesseract.image_to_string(img).strip()
                if ocr_text:
                    return f"OCR Text Extracted from Screen:\n{ocr_text}"

            return f"Screen snapshot captured at {screenshot_path}. OCR text extraction active."
        except Exception as e:
            return f"Failed to capture screen OCR text: {e}"

    def solve_screen_question(self) -> str:
        """Capture assignment question on screen and solve it using Laalaa AI."""
        screen_text = self.capture_screen_text()
        print(f"[ScreenOCRSolver] Solving assignment question from screen OCR...")

        prompt = (
            f"Solve this assignment question extracted from screen OCR clearly, step-by-step:\n\n"
            f"{screen_text}\n\n"
            f"Provide a step-by-step explanation and final clear answer."
        )

        if self.ai:
            solution = self.ai.generate(prompt)
            return f"📚 Assignment Solution for Screen Question:\n\n{solution}"

        return f"Assignment question captured from screen:\n{screen_text}"
