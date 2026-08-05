"""
Specialist role modes: LALA becomes your Researcher, Chief of Staff, Sales
lead, Developer, Strategist, Finance manager, Designer, or CRM.

- switching is a voice command ("switch to sales mode")
- the active role augments the LLM system prompt
- each role gets small deterministic tools (briefing, expenses, contacts…)
"""

import json
import os

from . import config

ROLES = {
    "researcher": "Researcher mode: synthesize topics fast, cite sources when known, "
                  "prefer structured findings (question → evidence → conclusion), and "
                  "suggest the next thing to read or verify.",
    "chief_of_staff": "Chief-of-Staff mode: run the user's day. Prioritize ruthlessly, "
                      "surface calendar conflicts and prep needs, draft crisp updates, "
                      "and keep a rolling list of open loops. Use the briefing tool when asked.",
    "sales": "Sales mode: think pipeline. Help with outreach angles, objection handling, "
             "discovery questions, follow-up cadence, and deal-next-steps. Keep energy high, "
             "language concrete.",
    "developer": "Developer mode: think in systems. Give precise technical answers, small "
                 "code sketches when useful, flag edge cases and complexity, and prefer "
                 "boring reliable technology.",
    "strategist": "Strategist mode: frame decisions with objectives, options, trade-offs and "
                  "second-order effects. Use SWOT/ports-style structure when asked; end with a "
                  "recommendation and the key assumption to test.",
    "finance": "Finance mode: be number-literate and conservative. Track expenses when asked, "
               "summarize spend, sanity-check unit economics, and always state assumptions and "
               "currency.",
    "design": "Design mode: think hierarchy, contrast, spacing and motion. Offer concrete "
              "directions (palette/type/layout), reference principles, and keep critique kind "
              "and actionable.",
    "crm": "CRM mode: keep relationships warm. Record contacts when asked, list them, suggest "
           "who to touch next and draft short personal follow-ups.",
}

ALIASES = {
    "chief of staff": "chief_of_staff", "chiefofstaff": "chief_of_staff",
    "research": "researcher", "dev": "developer", "strategy": "strategist",
    "finances": "finance", "designer": "design",
}

def normalize_role(text):
    t = (text or "").strip().lower()
    t = ALIASES.get(t, t)
    return t if t in ROLES else None


def prompt_for(role):
    return ROLES.get(role or "", "")


# ---------------------------------------------------------------- storage

def _path(name):
    return os.path.join(config.DATA_DIR, name)


def _load(name, fallback):
    try:
        with open(_path(name), "r", encoding="utf8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return fallback


def _save(name, value):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(_path(name), "w", encoding="utf8") as fh:
        json.dump(value, fh, indent=2)


# finance
def add_expense(amount, desc):
    rows = _load("finance.json", [])
    rows.append({"amount": amount, "desc": desc,
                 "ts": __import__("time").time()})
    _save("finance.json", rows)
    return rows


def finance_summary():
    rows = _load("finance.json", [])
    if not rows:
        return "No expenses recorded yet."
    total = sum(r.get("amount", 0) for r in rows)
    last = rows[-5:]
    return (f"Total recorded spend: {total:,.0f}. "
            "Recent: " + "; ".join(f"{r['desc']} ({r['amount']:,.0f})" for r in last) + ".")


# crm
def add_contact(name, company):
    rows = _load("crm.json", [])
    rows.append({"name": name, "company": company,
                 "ts": __import__("time").time()})
    _save("crm.json", rows)
    return rows


def contact_list():
    rows = _load("crm.json", [])
    if not rows:
        return "No contacts stored yet."
    return "Contacts: " + "; ".join(f"{r['name']} @ {r['company']}" for r in rows[-8:])


# chief of staff
def briefing(cfg):
    from . import calendar_store, weather

    parts = ["Here's your briefing."]
    cal = calendar_store.upcoming(5)
    parts.append("Calendar: " + ("; ".join(calendar_store.fmt(p) for p in cal)
                 if cal else "clear."))
    wx = weather.summary("")
    if wx:
        parts.append("Weather: " + wx)
    notes = _load("crm.json", [])
    if notes:
        parts.append(f"CRM: {len(notes)} contacts on file — consider a follow-up.")
    return " ".join(parts)
