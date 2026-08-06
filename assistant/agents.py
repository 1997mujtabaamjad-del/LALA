"""
Multi-agent brain. The CEO agent coordinates specialists instead of doing
everything itself:

  ceo        decomposes goals (planner), delegates, checks progress, summarizes
  research   web search / wiki / scholar verification
  coding     sandboxed python execution (confirm-gated) + file open
  vision     screen capture + OCR description
  security   permission gates + audit (security.py)
  finance    spend tracking + simple budget analysis
  scheduler  calendar + reminders + briefings
  health     habit logging (water/steps/sleep)
  home       lights / IoT / robotics passthrough
"""

import json
import os
import subprocess

from . import (autonomy, calendar_store, config, planner,
               robotics, roles, security, vision, websearch, world)


class Base:
    name = "base"

    def __init__(self, cfg, vault=None, confirm_fn=None):
        self.cfg = cfg
        self.vault = vault
        self.confirm_fn = confirm_fn

    def run(self, task):  # pragma: no cover - overridden
        raise NotImplementedError


class ResearchAgent(Base):
    name = "research"

    def run(self, task):
        ans = websearch.answer(task)
        if ans:
            return ans
        import webbrowser
        webbrowser.open(f"https://www.google.com/search?q={task}")
        return f"No instant source for “{task}” — opened a search."


class CodingAgent(Base):
    name = "coding"

    def run(self, task):
        if task.startswith("open"):
            import webbrowser
            webbrowser.open("https://github.com")
            return "Opened GitHub."
        if task.startswith(("run", "execute")):
            code = task.split(None, 1)[1] if " " in task else "print('hi')"
            ok, note = security.gate("coding", security.EXEC, self.confirm_fn,
                                     detail=code[:60])
            if not ok:
                return note
            try:
                r = subprocess.run([self.cfg.get("python_bin", "python3"), "-c", code],
                                   capture_output=True, timeout=10, text=True)
                return (r.stdout or r.stderr or "done")[:400]
            except Exception as e:  # noqa: BLE001
                return f"code failed: {e}"
        return "I can `run <python>` (confirmed) or open coding resources."


class VisionAgent(Base):
    name = "vision"

    def run(self, task):
        return vision.describe()


class FinanceAgent(Base):
    name = "finance"

    def run(self, task):
        rows = finance_store.rows()
        if not rows:
            return "No spending tracked yet — say “add expense 250 for coffee”."
        total = sum(r.get("amount", 0) for r in rows)
        avg = total / len(rows)
        top = max(rows, key=lambda r: r.get("amount", 0))
        return (f"Budget analysis: total {total:,.0f} over {len(rows)} items, "
                f"avg {avg:,.0f}; biggest: {top.get('desc')} ({top.get('amount'):,.0f}).")


class SchedulerAgent(Base):
    name = "scheduler"

    def run(self, task):
        t = task.lower()
        if "brief" in t:
            return roles.briefing(self.cfg)
        if "list" in t or "event" in t:
            ups = calendar_store.upcoming(5)
            return ("; ".join(calendar_store.fmt(p) for p in ups)
                    if ups else "Calendar clear.")
        if "reminder" in t:
            from datetime import datetime, timedelta
            autonomy.add_task("reminder", datetime.now() + timedelta(hours=1),
                              {"msg": task.replace("reminder", "").strip() or "follow up"})
            return "Reminder set for in 1 hour."
        return "Scheduler ready: briefings, events, reminders."


class HealthAgent(Base):
    name = "health"

    def run(self, task):
        return health_log(task)


class HomeAgent(Base):
    name = "home"

    def run(self, task):
        t = task.lower()
        if t.startswith("robot"):
            parts = t.split()
            return robotics.send(parts[1] if len(parts) > 1 else "",
                                 " ".join(parts[2:]) or "status") \
                if len(parts) > 1 else robotics.status()
        from . import lights
        op = "on" if "on" in t else "off" if "off" in t else "set"
        _ok, msg = lights.control(self.cfg, op)
        return msg


class CEOAgent(Base):
    """Coordinates: plan → delegate → check → summarize."""
    name = "ceo"

    AGENTS = None

    def _team(self):
        return {
            "research": ResearchAgent(self.cfg, self.vault, self.confirm_fn),
            "coding": CodingAgent(self.cfg, self.vault, self.confirm_fn),
            "vision": VisionAgent(self.cfg, self.vault, self.confirm_fn),
            "finance": FinanceAgent(self.cfg, self.vault, self.confirm_fn),
            "scheduler": SchedulerAgent(self.cfg, self.vault, self.confirm_fn),
            "health": HealthAgent(self.cfg, self.vault, self.confirm_fn),
            "home": HomeAgent(self.cfg, self.vault, self.confirm_fn),
            "ceo": self,
        }

    def execute(self, goal, announce=None):
        steps, plan_name = planner.plan(goal, self.cfg)
        team = self._team()
        report, done, checked = [], 0, 0
        for step in steps:
            agent = team.get(step.get("agent"), ResearchAgent(self.cfg))
            if step.get("agent") == "ceo":
                result = "Planned next: " + step["task"]
            else:
                result = agent.run(step["task"])
            # progress check before moving on
            ok = bool(result and result.strip() and "failed" not in result.lower())
            checked += 1 if ok else 0
            done += 1
            report.append(f"[{done}/{len(steps)}{'✔' if ok else '⚠'}] {agent.name}: {result}")
            if announce:
                announce(f"Step {done}/{len(steps)} {'done' if ok else 'skipped'} ({agent.name}).")
            if self.vault:
                self.vault.event(f"goal:{goal} step:{step['task']} → {result[:80]}")
        summary = (f"Goal “{goal}” via {plan_name}-plan "
                   f"({checked}/{len(steps)} steps verified): " +
                   " | ".join(r.split("] ", 1)[1][:90] for r in report))
        return summary, report


# ------------------------------------------------------------------ health

def _health_file():
    return os.path.join(config.DATA_DIR, "health.json")


def health_log(task):
    import re
    import time as _t

    rows = []
    try:
        rows = json.load(open(_health_file(), encoding="utf8"))
    except (OSError, ValueError):
        pass
    m = re.match(r"log (\w+) (\d+(?:\.\d+)?)", task.lower())
    if m:
        rows.append({"t": _t.time(), "metric": m.group(1), "value": float(m.group(2))})
        json.dump(rows[-500:], open(_health_file(), "w", encoding="utf8"))
        return f"Logged {m.group(1)}: {m.group(2)}."
    today = [r for r in rows if _t.time() - r["t"] < 86400]
    if not today:
        return "No health logs today. Say “log water 8” or “log steps 6000”."
    agg = {}
    for r in today:
        agg[r["metric"]] = agg.get(r["metric"], 0) + r["value"]
    return "Today: " + ", ".join(f"{k} {v:,.0f}" for k, v in agg.items()) + "."


# finance_store shim (roles holds the data; agents get a clean API)
finance_store = None


def _finance_rows():
    return roles._load("finance.json", [])


class _FS:
    @staticmethod
    def rows():
        return _finance_rows()


finance_store = _FS()
