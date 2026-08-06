"""
Long-term memory vault — five layers beyond chat history:

  working    in-memory ring (seconds/minutes)
  session    this run's events (hours)
  semantic   facts / preferences / projects / documents index
  episodic   timestamped events (conversations, meetings, sightings)
  procedural learned routines / macros ("how to do X")

Voiceprints live in profiles.py (consent-gated). Everything persists under
assistant/data/vault/. `recall()` does keyword-overlap retrieval across layers.
"""

import json
import os
import time
from collections import deque

from . import config

DIR = lambda: os.path.join(config.DATA_DIR, "vault")  # noqa: E731
LAYERS = ("session", "semantic", "episodic", "procedural")


class Vault:
    def __init__(self):
        os.makedirs(DIR(), exist_ok=True)
        self.working = deque(maxlen=50)

    # ------------------------------------------------------------ storage
    def _file(self, layer):
        return os.path.join(DIR(), f"{layer}.json")

    def _load(self, layer):
        try:
            with open(self._file(layer), "r", encoding="utf8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return []

    def _save(self, layer, rows):
        with open(self._file(layer), "w", encoding="utf8") as fh:
            json.dump(rows[-500:], fh, indent=2)

    # ------------------------------------------------------------ API
    def remember(self, layer, text, meta=None):
        row = {"t": time.time(), "text": text, "meta": meta or {}}
        if layer == "working":
            self.working.append(row)
        else:
            rows = self._load(layer)
            rows.append(row)
            self._save(layer, rows)
        return row

    def note(self, text):  # semantic shortcut
        return self.remember("semantic", text)

    def event(self, text):  # episodic shortcut
        return self.remember("episodic", text)

    def skill(self, name, steps):  # procedural
        return self.remember("procedural", name, {"steps": steps})

    def layer(self, name):
        return self._load(name) if name in LAYERS else list(self.working)

    def recall(self, query, limit=5):
        """Keyword-overlap retrieval across all layers."""
        qw = set(query.lower().split())
        scored = []
        sources = {"working": list(self.working)}
        for l in LAYERS:
            sources[l] = self._load(l)
        for layer, rows in sources.items():
            for row in rows:
                words = set(row["text"].lower().split())
                hit = len(qw & words)
                if hit:
                    scored.append((hit, layer, row["text"]))
        scored.sort(key=lambda x: -x[0])
        return [(l, t) for _h, l, t in scored[:limit]]
