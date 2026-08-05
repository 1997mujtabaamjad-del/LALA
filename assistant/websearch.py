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


def parse_wiki(payload):
    """Pure parser for Wikipedia REST summary responses."""
    if not payload or payload.get("type") == "disambiguation":
        return None
    text = (payload.get("extract") or "").strip()
    return text[:400] if text else None


def wiki_results(query, limit=3):
    """[(title, url)] via Wikipedia opensearch — a real, keyless web search."""
    try:
        r = requests.get("https://en.wikipedia.org/w/api.php",
                         params={"action": "opensearch", "search": query,
                                 "limit": limit, "format": "json"},
                         timeout=10)
        r.raise_for_status()
        _, titles, _, urls = r.json()
        return list(zip(titles, urls))
    except Exception:  # noqa: BLE001
        return []


def wiki_summary(query):
    try:
        r = requests.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(query)}",
                         timeout=10)
        if not r.ok:
            return None
        return parse_wiki(r.json())
    except Exception:  # noqa: BLE001
        return None


def answer(query):
    try:
        r = requests.get("https://api.duckduckgo.com/",
                         params={"q": query, "format": "json", "no_html": 1,
                                 "no_redirect": 1},
                         timeout=10)
        r.raise_for_status()
        text = parse_ddg(r.json())
    except Exception:  # noqa: BLE001
        text = None
    return text or wiki_summary(query)
