"""Scheduler engine for task scheduling, delayed execution, and due task checking."""

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

    def save(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.tasks, f, indent=2)
        except Exception as e:
            print(f"[SchedulerEngine] Save schedule error: {e}")

    def schedule_delay_command(self, action: str, delay_seconds: int) -> str:
        """Schedule a command to run after delay_seconds (e.g. 5m baad lock screen)."""
        now = time.time()
        new_task = {
            "action": action,
            "enabled": True,
            "last_run": now,
            "next_run": now + delay_seconds,
            "interval_seconds": 99999999
        }
        self.tasks.append(new_task)
        self.save()
        mins = int(delay_seconds / 60) if delay_seconds >= 60 else delay_seconds
        unit = "minutes" if delay_seconds >= 60 else "seconds"
        return f"Task '{action}' scheduled to execute in {mins} {unit}."

    def due_tasks(self) -> list:
        now = time.time()
        due = []
        remaining = []
        for task in self.tasks:
            if task.get("enabled", True):
                next_run = task.get("next_run", 0)
                if now >= next_run:
                    due.append(task)
                    interval = task.get("interval_seconds", 3600)
                    if interval < 80000000: # Recurring task
                        task["last_run"] = now
                        task["next_run"] = now + interval
                        remaining.append(task)
                else:
                    remaining.append(task)
            else:
                remaining.append(task)

        if due:
            self.tasks = remaining
            self.save()

        return due
