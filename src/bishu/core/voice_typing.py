"""Voice Typing & Text Dictation Engine for active window typing."""

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False


class VoiceTypingEngine:
    """Voice Typing & Text Dictation Agent for active cursor typing."""

    def dictate_text(self, text: str) -> str:
        """Type spoken text directly into active application cursor."""
        if not text:
            return "No text provided for voice dictation."

        if HAS_PYAUTOGUI and pyautogui:
            pyautogui.write(text, interval=0.03)
            return f"🎙️ Dictated & typed text into cursor: '{text}'"

        return f"Voice dictation text: '{text}'"

    def type_clipboard_contents(self) -> str:
        """Read system clipboard and type contents directly into active window."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            clip_text = root.clipboard_get()
            root.destroy()
            if clip_text and HAS_PYAUTOGUI and pyautogui:
                pyautogui.write(clip_text, interval=0.02)
                return f"📋 Typed clipboard contents into cursor ({len(clip_text)} characters)."
        except Exception:
            pass

        return "Clipboard empty or unavailable."
