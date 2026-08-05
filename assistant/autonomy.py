"""
Autonomous LALA: proactive behavior on top of reactive voice.

- scheduler thread ticks every 30 s and fires due tasks:
    reminder       one-shot at a time ("remind me to call asha at 5pm")
    briefing       daily at HH:MM ("every day at 9am brief me")
    calendar_watch heads-up 15 min before events ("watch my calendar")
    weather_watch  rain/storm alert ("watch the weather")
- run_goal(): autonomous agent loop — the LLM plans and executes tool
  steps by itself (bounded rounds) and reports a final summary.

Announcements go to the provided callback (speak + log).
"""

import json
import os
import threading
import time
from datetime import datetime, timedelta

from . import calendar_store, config, llm, roles, tools, weather

FILE = lambda: os.path.join(config.DATA_DIR, "autonomy.json")  # noqa: E731


def load_tasks():
    try:
        with open(FILE(), "r", encoding="utf8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return []


def save_tasks(tasks):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(FILE(), "w", encoding="utf8") as fh:
        json.dump(tasks, fh, indent=2)


def add_task(kind, when=None, payload=None):
    tasks = load_tasks()
    tasks.append({"id": f"t{len(tasks)}{int(time.time())}", "kind": kind,
                  "when": when.isoformat() if isinstance(when, datetime) else when,
                  "payload": payload or {}, "done": False,
                  "created": datetime.now().isoformat()})
    save_tasks(tasks)
    return tasks[-1]


def parse_reminder(text):
    """'remind me to call asha at 5pm' -> (when, message) or (None, None)."""
    from . import calendar_store as cs

    when = cs.parse_when(text)
    if not when:
        return None, None
    msg = text
    msg = msg.split(" at ", 1)[0]
    msg = msg.replace("remind me to", "").replace("remind me", "").strip()
    return when, (msg or "your reminder")


# ------------------------------------------------------------------ runner

def run_task(task, cfg):
    """Returns an announcement string, or None for 'nothing to say'."""
    kind = task["kind"]
    now = datetime.now()
    if kind == "reminder":
        return f"Reminder: {task['payload'].get('msg', 'something')}."
    if kind == "briefing":
        return roles.briefing(cfg)
    if kind == "calendar_watch":
        for when, ev in calendar_store.upcoming(8):
            delta = (when - now).total_seconds() / 60
            if 0 <= delta <= 15:
                return f"Heads up — {ev['title']} starts in {int(delta)} minutes."
        return None
    if kind == "weather_watch":
        wx = weather.summary("") or ""
        if any(w in wx.lower() for w in ("rain", "storm", "drizzle", "thunder")):
            return f"Weather alert: {wx}"
        return None
    return None


def due_tasks(now=None):
    now = now or datetime.now()
    out = []
    tasks = load_tasks()
    changed = False
    for t in tasks:
        if t.get("done"):
            continue
        if t["kind"] in ("calendar_watch", "weather_watch"):
            # recurring: every 5 minutes, throttled by last_run
            last = t.get("last_run")
            if not last or (now - datetime.fromisoformat(last)) > timedelta(minutes=5):
                out.append(t)
                t["last_run"] = now.isoformat()
                changed = True
        elif t.get("when"):
            when = datetime.fromisoformat(t["when"])
            if when <= now:
                out.append(t)
                if t["kind"] == "briefing":
                    t["when"] = (when + timedelta(days=1)).isoformat()  # daily
                else:
                    t["done"] = True
                changed = True
    if changed:
        save_tasks(tasks)
    return out


class Autonomy(threading.Thread):
    """Background daemon: fires due tasks through the announce callback."""

    def __init__(self, cfg, announce, interval=30):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.announce = announce
        self.interval = interval
        self._stop = threading.Event()

    def run(self):
        while not self._stop.wait(self.interval):
            try:
                for task in due_tasks():
                    text = run_task(task, self.cfg)
                    if text:
                        self.announce(text)
            except Exception:  # noqa: BLE001 — autonomy must never crash the app
                pass

    def stop(self):
        self._stop.set()


# ------------------------------------------------------- autonomous goals

GOAL_SYSTEM = (
    "You are LALA in AUTONOMOUS mode. The user gave you a goal. Plan silently, "
    "use the provided tools step by step to accomplish it, and finish with a "
    "short spoken summary of what you did. If a step fails, adapt or skip it."
)


def run_goal(goal, cfg, max_rounds=6):
    """Bounded autonomous agent loop. Returns (summary, executed_steps)."""
    steps = []
    messages = [{"role": "system", "content": GOAL_SYSTEM},
                {"role": "user", "content": goal}]
    provider = llm.resolve_provider(cfg)
    for _ in range(max_rounds):
        if provider == "openai" and cfg.get("openai_api_key"):
            msg = _chat_openai(cfg, messages)
        elif provider == "ollama":
            msg = _chat_ollama(cfg, messages)
        else:
            return (f"I'd work on “{goal}” with research, calendar and web tools — "
                    "connect Ollama or an OpenAI key to unlock autonomous mode."), steps
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or "Done.", steps
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            steps.append(f"{name}({args})")
            result = tools.execute_tool(name, args, cfg)
            messages.append({"role": "tool", "tool_call_id": call.get("id", "c"),
                             "content": result})
    return "Reached my step limit — here's where I got to.", steps


def _chat_openai(cfg, messages):
    import requests

    r = requests.post("https://api.openai.com/v1/chat/completions",
                      headers={"Authorization": f"Bearer {cfg['openai_api_key']}"},
                      json={"model": cfg.get("openai_model", "gpt-4o-mini"),
                            "messages": messages, "tools": tools.TOOLS},
                      timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]


def _chat_ollama(cfg, messages):
    import requests

    r = requests.post(cfg["ollama_url"] + "/api/chat",
                      json={"model": cfg["ollama_model"], "messages": messages,
                            "tools": tools.TOOLS, "stream": False},
                      timeout=60)
    r.raise_for_status()
    return r.json()["message"]
