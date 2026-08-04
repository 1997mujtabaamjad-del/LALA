"""
Conversation memory + long-term notes.

- Chat history is persisted to assistant/data/memory.json so the assistant
  remembers previous conversations across sessions.
- Long-term notes ("remember that I like tea") live in data/notes.json and are
  always injected into the system prompt.
"""

import json
import os
import time

from . import config

MEMORY_FILE = os.path.join(config.DATA_DIR, "memory.json")
NOTES_FILE = os.path.join(config.DATA_DIR, "notes.json")


class Memory:
    def __init__(self):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        self.history = self._read(MEMORY_FILE, [])
        self.notes = self._read(NOTES_FILE, [])

    @staticmethod
    def _read(path, fallback):
        try:
            with open(path, "r", encoding="utf8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return fallback

    @staticmethod
    def _write(path, value):
        with open(path, "w", encoding="utf8") as fh:
            json.dump(value, fh, indent=2)

    # ---- chat history ----
    def add(self, role, content):
        self.history.append({"role": role, "content": content, "ts": int(time.time())})
        # keep the file bounded
        if len(self.history) > 400:
            self.history = self.history[-400:]
        self._write(MEMORY_FILE, self.history)

    def recent(self, n):
        return [{"role": m["role"], "content": m["content"]} for m in self.history[-n:]]

    def clear(self):
        self.history = []
        self._write(MEMORY_FILE, self.history)

    # ---- long-term notes ----
    def add_note(self, text):
        self.notes.append({"text": text, "ts": int(time.time())})
        self._write(NOTES_FILE, self.notes)

    def notes_text(self):
        return "; ".join(n["text"] for n in self.notes[-20:])
