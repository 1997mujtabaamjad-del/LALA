"""Path helpers for Bishu data storage."""

from pathlib import Path


def bishu_dir() -> Path:
    d = Path.home() / ".bishu"
    d.mkdir(parents=True, exist_ok=True)
    return d


def memory_file() -> Path:
    return bishu_dir() / "memory.json"


def schedule_file() -> Path:
    return bishu_dir() / "schedule.json"
