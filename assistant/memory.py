"""
Conversation memory + long-term notes.
Paths resolve from config.DATA_DIR at call time (so tests/audits can redirect).
"""

import json
import os
import time

from . import config


class Memory:
    def __init__(self):
        self._h = None
        self._n = None

    # ------------------------------------------------------------ paths
    def _mem_file(self):
        return os.path.join(config.DATA_DIR, "memory.json")

    def _notes_file(self):
        return os.path.join(config.DATA_DIR, "notes.json")

    # ------------------------------------------------------------ io
    @staticmethod
    def _read(path, fallback):
        try:
            with open(path, "r", encoding="utf8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return fallback

    @staticmethod
    def _write(path, value):
        os.makedirs(config.DATA_DIR, exist_ok=True)
        with open(path, "w", encoding="utf8") as fh:
            json.dump(value, fh, indent=2)

    # ------------------------------------------------------------ history
    @property
    def history(self):
        if self._h is None:
            self._h = self._read(self._mem_file(), [])
        return self._h

    @property
    def notes(self):
        if self._n is None:
            self._n = self._read(self._notes_file(), [])
        return self._n

    def add(self, role, content):
        self.history.append({"role": role, "content": content, "ts": int(time.time())})
        if len(self.history) > 400:
            self._h = self.history[-400:]
        self._write(self._mem_file(), self.history)

    def recent(self, n):
        return [{"role": m["role"], "content": m["content"]} for m in self.history[-n:]]

    def clear(self):
        self._h = []
        self._write(self._mem_file(), self._h)

    # ------------------------------------------------------------ notes
    def add_note(self, text):
        self.notes.append({"text": text, "ts": int(time.time())})
        self._write(self._notes_file(), self.notes)

    def notes_text(self):
        return "; ".join(n["text"] for n in self.notes[-20:])
