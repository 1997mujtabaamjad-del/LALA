"""
Digital twin — a live, queryable representation of the user's environment:
processes · files · devices · lights · (browser tabs where available).
`refresh()` stores a snapshot; `diff()` reports what changed since last time.
"""

import json
import os
import time

from . import config, world

FILE = lambda: os.path.join(config.DATA_DIR, "twin.json")  # noqa: E731


def _file_index():
    """Count + recently-touched docs in ~/Documents (cheap, no content read)."""
    home = os.path.expanduser("~")
    docs = os.path.join(home, "Documents")
    count, recent = 0, []
    try:
        for root, _dirs, files in os.walk(docs):
            for f in files:
                count += 1
                if count > 5000:
                    break
            if count > 5000:
                break
        recent = sorted(
            (os.path.join(docs, f) for f in os.listdir(docs)
             if os.path.isfile(os.path.join(docs, f))),
            key=os.path.getmtime, reverse=True)[:5]
    except OSError:
        pass
    return {"count": count, "recent": [os.path.basename(p) for p in recent]}


def refresh(cfg=None):
    state = {
        "ts": time.time(),
        "world": world.snapshot(cfg),
        "files": _file_index(),
    }
    try:
        prev = json.load(open(FILE(), encoding="utf8"))
    except (OSError, ValueError):
        prev = None
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(FILE(), "w", encoding="utf8") as fh:
        json.dump(state, fh, indent=2)
    return state, prev


def diff():
    state, prev = refresh()
    if not prev:
        return "First twin snapshot taken — I now mirror your environment."
    changes = []
    pw, w = prev["world"], state["world"]
    if pw["network"] != w["network"]:
        changes.append(f"network went {w['network']}")
    if pw["battery"] != w["battery"]:
        changes.append(f"battery {w['battery']}")
    new_top = set(w["top_processes"]) - set(pw["top_processes"])
    if new_top:
        changes.append("new apps: " + ", ".join(list(new_top)[:3]))
    nf = state["files"]["recent"][:1]
    pf = prev.get("files", {}).get("recent", [])[:1]
    if nf and nf != pf:
        changes.append(f"newest doc: {nf[0]}")
    return ("Changes since last look: " + "; ".join(changes) + ".") if changes \
        else "All quiet — nothing changed since my last look."
