"""
Digital twin — a live, queryable representation of the user's environment:
processes · files · devices · lights · (browser tabs where available).
`refresh()` stores a snapshot; `diff()` reports what changed since last time.
"""

import json
import os
import subprocess
import sys
import time

from . import config, world

FILE = lambda: os.path.join(config.DATA_DIR, "twin.json")  # noqa: E731
PLATFORM = {"win32": "win", "darwin": "mac"}.get(sys.platform, "linux")
BROWSERS_RE = "chrome|msedge|firefox|brave|safari|chromium"


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=6, text=True,
                           shell=isinstance(cmd, str))
        return r.stdout if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def _browser_tabs():
    """Visible browser tab/window titles per OS."""
    if PLATFORM == "win":
        ps = ("Get-Process | Where-Object {$_.MainWindowTitle -and "
              "($_.ProcessName -match '" + BROWSERS_RE + "')} | "
              "Select-Object -First 8 -ExpandProperty MainWindowTitle")
        return [l.strip() for l in
                _run(["powershell", "-NoProfile", "-Command", ps]).splitlines()
                if l.strip()]
    if PLATFORM == "mac":
        titles = []
        for app in ("Google Chrome", "Safari", "Microsoft Edge", "Firefox"):
            out = _run(['osascript', '-e',
                        f'tell application "System Events" to get name of '
                        f'every window of process "{app}"'])
            titles += [t.strip() for t in out.split(",") if t.strip()]
        return titles[:8]
    out = _run("wmctrl -l") or _run("xdotool search --onlyvisible --name . getwindowname %@")
    return [l.split(None, 3)[-1] for l in out.splitlines() if l.strip()][:8]


def _displays():
    """Desktop layout: connected displays + resolutions."""
    if PLATFORM == "linux":
        lines = [l for l in _run("xrandr --listmonitors").splitlines()[1:] if l.strip()]
        if lines:
            return [l.split()[1] if len(l.split()) > 1 else l.strip() for l in lines]
        return [l.split(" connected ")[0] for l in _run("xrandr").splitlines()
                if " connected " in l]
    if PLATFORM == "mac":
        return [l.strip() for l in _run("system_profiler SPDisplaysDataType").splitlines()
                if "Resolution" in l][:4]
    out = _run("WMIC PATH Win32_VideoController Get CurrentHorizontalResolution,"
               "CurrentVerticalResolution /FORMAT:LIST")
    cur = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            cur[k.strip()] = v.strip()
    if cur.get("CurrentHorizontalResolution"):
        return [f"{cur['CurrentHorizontalResolution']}x{cur['CurrentVerticalResolution']}"]
    return []


def _cloud():
    """Local cloud-storage folders + file counts + freshness."""
    import glob as _g

    home = os.path.expanduser("~")
    roots = [("Dropbox", os.path.join(home, "Dropbox")),
             ("Google Drive", os.path.join(home, "Google Drive*")),
             ("OneDrive", os.path.join(home, "OneDrive*")),
             ("iCloud", os.path.join(home, "Library", "Mobile Documents"))]
    out = []
    for name, pat in roots:
        for root in _g.glob(pat):
            if not os.path.isdir(root):
                continue
            count, newest = 0, 0
            try:
                for r, _d, files in os.walk(root):
                    for f in files:
                        count += 1
                        try:
                            newest = max(newest, os.path.getmtime(os.path.join(r, f)))
                        except OSError:
                            pass
                    if count > 5000:
                        break
            except OSError:
                continue
            age = (time.time() - newest) / 3600 if newest else 0
            out.append(f"{name}: {count} files, last change {age:.1f}h ago")
    return out or ["no local cloud folders found"]


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
        "tabs": _browser_tabs(),
        "displays": _displays(),
        "cloud": _cloud(),
    }
    from . import extras

    state["downloads"] = extras.fresh_downloads(60)
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
    pt, st = prev.get("tabs", []), state.get("tabs", [])
    new_tabs = [t for t in st if t not in pt]
    closed = [t for t in pt if t not in st]
    if new_tabs:
        changes.append("opened tabs: " + ", ".join(new_tabs[:3]))
    if closed:
        changes.append("closed tabs: " + ", ".join(closed[:3]))
    pc, sc = prev.get("cloud", []), state.get("cloud", [])
    if pc != sc:
        changes.append("cloud: " + "; ".join(sc[:2]))
    pd, sd = prev.get("displays", []), state.get("displays", [])
    if pd != sd:
        changes.append("display layout changed")
    return ("Changes since last look: " + "; ".join(changes) + ".") if changes \
        else "All quiet — nothing changed since my last look."
