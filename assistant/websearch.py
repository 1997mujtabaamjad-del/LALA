"""
Spoken web answers via DuckDuckGo Instant Answer API (free, no key).
Falls back to opening the browser when there's no instant answer.
"""

import requests


def parse_ddg(payload):
    """Pure parser (unit-tested): best speakable text from a DDG IA response."""
    text = payload.get("AbstractText") or payload.get("Answer") or ""
    if not text:
        topics = payload.get("RelatedTopics") or []
        if topics:
            text = topics[0].get("Text", "")
    text = (text or "").strip()
    return text[:400] if text else None


def answer(query):
    try:
        r = requests.get("https://api.duckduckgo.com/",
                         params={"q": query, "format": "json", "no_html": 1,
                                 "no_redirect": 1},
                         timeout=10)
        r.raise_for_status()
        return parse_ddg(r.json())
    except Exception:  # noqa: BLE001
        return None
