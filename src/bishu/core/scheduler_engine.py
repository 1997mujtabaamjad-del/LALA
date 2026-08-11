"""Scheduler engine for task scheduling and due task checking."""

import json
import time
from pathlib import Path


class SchedulerEngine:
    """Schedule manager that checks and yields due tasks."""

    def __init__(self, filepath: Path):
        self.filepath = Path(filepath)
        self.tasks = []
        self.reload()

    def reload(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self.tasks = json.load(f)
            except Exception as e:
                print(f"[SchedulerEngine] Error reading schedule: {e}")
                self.tasks = []
        else:
            self.tasks = []

    def due_tasks(self) -> list:
        now = time.time()
        due = []
        for task in self.tasks:
            if task.get("enabled", True):
                next_run = task.get("next_run", 0)
                if now >= next_run:
                    due.append(task)
                    interval = task.get("interval_seconds", 3600)
                    task["last_run"] = now
                    task["next_run"] = now + interval
        return due
