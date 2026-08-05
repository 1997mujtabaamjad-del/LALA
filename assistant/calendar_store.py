"""
Tiny voice calendar: add / list events, persisted to assistant/data/calendar.json.
Understands “today / tomorrow / <weekday>” + “at 3pm / at 15:30”.
"""

import json
import os
import re
from datetime import datetime, timedelta

from . import config

FILE = os.path.join(config.DATA_DIR, "calendar.json")

DAYS = {"monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
        "friday": 4, "saturday": 5, "sunday": 6}

TITLE_SPLIT = re.compile(
    r"\b(?:today|tomorrow|tonight|monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|at)\b"
)


def load():
    try:
        with open(FILE, "r", encoding="utf8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def save(events):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(FILE, "w", encoding="utf8") as fh:
        json.dump(events, fh, indent=2)


def parse_when(text):
    """Return a datetime or None. Defaults: today, time required."""
    t = (text or "").lower()
    m = re.search(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", t)
    if not m:
        return None
    hour = int(m.group(1))
    minute = int(m.group(2) or 0)
    ampm = m.group(3)
    if ampm == "pm" and hour < 12:
        hour += 12
    if ampm == "am" and hour == 12:
        hour = 0

    now = datetime.now()
    if "tomorrow" in t:
        day = (now + timedelta(days=1)).date()
    elif "today" in t or "tonight" in t:
        day = now.date()
    else:
        day = None
        for name, idx in DAYS.items():
            if re.search(rf"\b{name}\b", t):
                delta = (idx - now.weekday()) % 7 or 7
                day = (now + timedelta(days=delta)).date()
                break
        day = day or now.date()
    if minute > 59 or hour > 23:
        return None
    return datetime(day.year, day.month, day.day, hour, minute)


def split_title(text):
    return TITLE_SPLIT.split(text, 1)[0].strip(" ,;-") or "event"


def add(title, when_text):
    when = parse_when(when_text)
    if not when:
        return None
    events = load()
    event = {"id": f"ev{len(events)}{int(when.timestamp())}",
             "when": when.isoformat(), "title": title}
    events.append(event)
    save(events)
    return event


def upcoming(limit=5, on_day=None):
    now = datetime.now()
    events = []
    for e in load():
        try:
            when = datetime.fromisoformat(e["when"])
        except (ValueError, KeyError):
            continue
        if when >= now - timedelta(hours=1):
            if on_day and when.date() != on_day:
                continue
            events.append((when, e))
    events.sort(key=lambda p: p[0])
    return events[:limit]


def fmt(event_pair):
    when, e = event_pair
    return f"{e['title']} — {when:%a %I:%M %p}".replace("  ", " ")
