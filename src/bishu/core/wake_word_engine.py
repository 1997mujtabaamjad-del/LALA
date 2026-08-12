"""Automatic Continuous Hands-Free Wake Word Detection Engine for Laalaa."""

import time
import re


class WakeWordEngine:
    """Continuous Hands-Free Wake Word Spotter for Laalaa."""

    WAKE_WORDS = ["laalaa", "lala", "hey laalaa", "hey lala", "assalam", "aadaab", "namaste", "bishu", "hey bishu"]

    def __init__(self, stt_engine=None):
        self.stt = stt_engine
        self.last_wake_time = 0.0

    def check_wake_word(self, audio_data) -> tuple:
        """Check in-memory audio buffer for automatic wake words."""
        now = time.time()
        if now - self.last_wake_time < 2.0: # Debounce wake triggers
            return False, "", ""

        if not self.stt:
            from bishu.core.stt_engine import STTEngine
            self.stt = STTEngine()

        transcribed_text = self.stt.transcribe_buffer(audio_data)
        if not transcribed_text:
            return False, "", ""

        text_lower = transcribed_text.lower().strip()
        print(f"[WakeWordEngine] Continuous audio transcribed: '{text_lower}'")

        # Check for wake words
        for ww in self.WAKE_WORDS:
            if ww in text_lower:
                self.last_wake_time = now
                # Extract trailing command after wake word if present
                cmd_part = re.sub(r'^.*?\b' + re.escape(ww) + r'\b\s*', '', text_lower).strip()
                print(f"[WakeWordEngine] 🎙️ AUTOMATIC WAKE WORD DETECTED: '{ww}' (Command: '{cmd_part}')")
                return True, ww, cmd_part

        return False, "", transcribed_text
