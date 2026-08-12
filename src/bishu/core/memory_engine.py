"""Memory engine for persistent key-value storage."""

import json
from pathlib import Path


class MemoryEngine:
    """JSON-backed persistent key-value store."""

    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.data = {}
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"[MemoryEngine] Failed to load memory file {self.filepath}: {e}")
                self.data = {}
        else:
            self.data = {}

    def save(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2)
        except Exception as e:
            print(f"[MemoryEngine] Failed to save memory file {self.filepath}: {e}")

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value
        self.save()
