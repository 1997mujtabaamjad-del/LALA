"""Notepad Document Writer Agent for composing letters, leave applications, and auto-writing memos."""

import os
import sys
import time
import subprocess
from pathlib import Path


class DocumentWriterAgent:
    """Document Writer for auto-generating letters, leave applications, and memos in Notepad."""

    def __init__(self, ai_engine=None):
        self.ai = ai_engine
        self.output_dir = Path.home() / ".bishu" / "documents"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _open_in_notepad(self, file_path: Path):
        """Open generated document directly in Windows Notepad."""
        try:
            if os.name == "nt" and hasattr(os, "startfile"):
                os.startfile(str(file_path))
            else:
                subprocess.Popen(["notepad.exe", str(file_path)], shell=True)
        except Exception:
            pass

    def compose_letter(self, recipient: str, topic: str) -> str:
        """Compose formal or informal letter and open in Notepad."""
        print(f"[DocumentWriterAgent] Composing letter for '{recipient}' on '{topic}'...")

        prompt = (
            f"Write a professional, well-formatted letter addressed to '{recipient}' regarding '{topic}'.\n"
            f"Include Date, Salutation, Subject Line, Body Paragraphs, and Formal Closing."
        )

        content = ""
        if self.ai:
            content = self.ai.generate(prompt)

        if not content or len(content) < 50:
            content = (
                f"Date: {time.strftime('%Y-%m-%d')}\n"
                f"To: {recipient}\n\n"
                f"Subject: Formal Letter Regarding {topic}\n\n"
                f"Dear {recipient},\n\n"
                f"I am writing this letter to bring to your attention {topic}.\n\n"
                f"Sincerely,\nLaalaa Document Writer"
            )

        file_path = self.output_dir / f"Letter_{int(time.time())}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._open_in_notepad(file_path)
        return f"Formal letter for '{recipient}' composed and opened in Notepad ({file_path.name})."

    def compose_leave_application(self, reason: str = "personal work", days: int = 2) -> str:
        """Compose formal leave application letter for job/college and open in Notepad."""
        print(f"[DocumentWriterAgent] Composing {days}-day leave application for '{reason}'...")

        prompt = (
            f"Write a formal leave application letter for {days} days due to '{reason}'.\n"
            f"Include To Manager/Principal, Subject, Body, and Respectful Closing."
        )

        content = ""
        if self.ai:
            content = self.ai.generate(prompt)

        if not content or len(content) < 50:
            content = (
                f"Date: {time.strftime('%Y-%m-%d')}\n"
                f"To: The Manager / Principal\n\n"
                f"Subject: Leave Application for {days} Days Due to {reason.title()}\n\n"
                f"Respected Sir/Madam,\n\n"
                f"I am writing to formally request {days} days leave from duty due to {reason}.\n"
                f"Kindly grant me leave for the specified duration.\n\n"
                f"Thanking you,\nYours sincerely,\n[Your Name]"
            )

        file_path = self.output_dir / f"Leave_Application_{int(time.time())}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._open_in_notepad(file_path)
        return f"Leave application for {days} days composed and opened in Notepad ({file_path.name})."

    def write_memo(self, title: str, notes: str) -> str:
        """Auto-write office memo or meeting notes and open in Notepad."""
        content = (
            f"========================================================\n"
            f"  OFFICE MEMORANDUM: {title.upper()}\n"
            f"  Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"========================================================\n\n"
            f"NOTES & ACTION ITEMS:\n{notes}\n\n"
            f"-- Recorded by Laalaa AI Assistant"
        )

        file_path = self.output_dir / f"Memo_{int(time.time())}.txt"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        self._open_in_notepad(file_path)
        return f"Memo '{title}' auto-written and opened in Notepad ({file_path.name})."
