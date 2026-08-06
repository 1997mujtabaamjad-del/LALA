"""
Autonomous planning: decompose a goal into agent steps, track progress.
LLM plans when available (JSON steps); otherwise proven templates.
"""

import json
import re

from . import llm

TEMPLATES = {
    "interview": [
        {"agent": "research", "task": "the company: what they do, size, recent news"},
        {"agent": "research", "task": "last 3 news items about the company"},
        {"agent": "coding", "task": "open the résumé file if findable"},
        {"agent": "ceo", "task": "draft 5 likely interview questions"},
        {"agent": "scheduler", "task": "reminder 1h before the interview: review notes"},
    ],
    "morning": [
        {"agent": "scheduler", "task": "briefing"},
        {"agent": "research", "task": "today's weather"},
        {"agent": "scheduler", "task": "list today's events"},
    ],
    "trip": [
        {"agent": "research", "task": "weather at destination"},
        {"agent": "scheduler", "task": "check calendar conflicts"},
        {"agent": "finance", "task": "spend summary for budgeting"},
    ],
}


def _template(goal):
    g = goal.lower()
    if "interview" in g:
        return TEMPLATES["interview"], "interview-prep"
    if "morning" in g or "day" in g:
        return TEMPLATES["morning"], "morning"
    if "trip" in g or "travel" in g:
        return TEMPLATES["trip"], "trip"
    return [{"agent": "research", "task": goal},
            {"agent": "scheduler", "task": f"reminder: follow up on {goal}"},
            {"agent": "ceo", "task": f"summarize progress on {goal}"}], "generic"


def plan(goal, cfg):
    """Returns (steps, plan_name). Prefers LLM JSON; falls back to templates."""
    provider = llm.resolve_provider(cfg)
    if provider in ("openai", "ollama"):
        try:
            raw = llm.ask(cfg, None,
                          f"Decompose this goal into JSON steps, each "
                          f'{{"agent": one of research|coding|vision|finance|'
                          f'scheduler|health|home|ceo, "task": string}}. '
                          f"Goal: {goal}. Reply with ONLY the JSON array.")
            m = re.search(r"\[.*\]", raw, re.S)
            steps = json.loads(m.group(0)) if m else None
            if steps and all("agent" in s and "task" in s for s in steps):
                return steps, "llm"
        except Exception:  # noqa: BLE001
            pass
    return _template(goal)
