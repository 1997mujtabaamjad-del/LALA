"""OCR Screen Text Clicker & Button Emulation Engine."""

import time
from pathlib import Path

try:
    import pyautogui
    from PIL import Image
    HAS_SCREEN_CLICK = True
except Exception:
    pyautogui = None
    Image = None
    HAS_SCREEN_CLICK = False

try:
    import pytesseract
    HAS_TESSERACT = True
except Exception:
    pytesseract = None
    HAS_TESSERACT = False


class OCRClickerEngine:
    """OCR Screen Text Clicker for finding on-screen button text and emulating mouse clicks."""

    def __init__(self):
        self.shots_dir = Path.home() / ".bishu" / "ocr_clicker_snaps"
        self.shots_dir.mkdir(parents=True, exist_ok=True)

    def click_button_text(self, target_text: str) -> str:
        """Find target text on screen using OCR and click its coordinates."""
        if not HAS_SCREEN_CLICK or not pyautogui:
            return "Screen clicker libraries (pyautogui / Pillow) not available."

        try:
            screenshot_path = self.shots_dir / f"click_snap_{int(time.time())}.png"
            shot = pyautogui.screenshot()
            shot.save(str(screenshot_path))

            if HAS_TESSERACT and pytesseract:
                img = Image.open(screenshot_path)
                data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
                
                target = target_text.lower().strip()
                for i in range(len(data['text'])):
                    word = data['text'][i].lower().strip()
                    if target in word and int(data['conf'][i]) > 30:
                        x = data['left'][i] + data['width'][i] // 2
                        y = data['top'][i] + data['height'][i] // 2
                        pyautogui.click(x, y)
                        return f"🖱️ OCR Clicker: Clicked button text '{target_text}' at screen coordinates ({x}, {y})."

            # Fallback center screen click
            sw, sh = pyautogui.size()
            pyautogui.click(sw // 2, sh // 2)
            return f"🖱️ OCR Clicker: Clicked center screen for target '{target_text}'."
        except Exception as e:
            return f"OCR clicker info: {e}"
