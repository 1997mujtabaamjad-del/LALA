"""
Deterministic voice commands (run BEFORE the LLM): open apps/websites,
search, weather, time/date, volume, power, notes.

`handle(text, memory)` returns (response_text, action).
`perform(action)` executes the side effect. Both are importable/testable.
"""

import platform
import random
import re
import shutil
import subprocess
import webbrowser
from datetime import datetime
from urllib.parse import quote

from . import calendar_store, lights, roles, websearch, weather

JOKES = [
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I told my computer I needed a break, and it said: no problem, I'll go to sleep.",
    "Why did the developer go broke? Because he used up all his cache.",
    "There are only 10 kinds of people: those who understand binary and those who don't.",
    "I would tell you a UDP joke, but you might not get it.",
]

SYSTEM = platform.system()  # Windows | Darwin | Linux

APPS = {
    # name: per-OS candidates (URIs are opened with webbrowser)
    "youtube": {"url": "https://www.youtube.com"},
    "google": {"url": "https://www.google.com"},
    "github": {"url": "https://www.github.com"},
    "gmail": {"url": "https://mail.google.com"},
    "maps": {"url": "https://maps.google.com"},
    "chatgpt": {"url": "https://chat.openai.com"},
    "whatsapp": {"url": "https://web.whatsapp.com"},
    "twitter": {"url": "https://x.com"},
    "x": {"url": "https://x.com"},
    "reddit": {"url": "https://www.reddit.com"},
    "netflix": {"url": "https://www.netflix.com"},
    "linkedin": {"url": "https://www.linkedin.com"},
    "spotify": {"win": ["spotify.exe"], "mac": ["Spotify"], "linux": ["spotify"]},
    "terminal": {"win": ["wt.exe", "cmd.exe"], "mac": ["Terminal"], "linux": ["gnome-terminal", "konsole", "xterm"]},
    "notepad": {"win": ["notepad.exe"], "mac": ["TextEdit"], "linux": ["gedit", "kate", "mousepad"]},
    "calculator": {"win": ["calc.exe"], "mac": ["Calculator"], "linux": ["gnome-calculator", "kcalc"]},
    "files": {"win": ["explorer.exe"], "mac": ["Finder"], "linux": ["nautilus", "dolphin", "thunar"]},
    "vs code": {"win": ["code.cmd"], "mac": ["Visual Studio Code"], "linux": ["code"]},
    "vscode": {"win": ["code.cmd"], "mac": ["Visual Studio Code"], "linux": ["code"]},
    "browser": {"win": ["msedge.exe", "chrome.exe"], "mac": ["Google Chrome", "Safari"], "linux": ["google-chrome", "firefox", "chromium"]},
    "camera": {"win": ["microsoft.windows.camera:"], "mac": ["Photo Booth"], "linux": ["cheese"]},
}


def _norm(text):
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def _first(*cmds):
    for c in cmds:
        if shutil.which(c):
            return c
    return None


def handle(text, memory=None):
    """Return (response, action) or (None, None) when not a command."""
    t = _norm(text)

    m = re.match(r"^(?:open|launch) (.+)$", t)
    if m:
        target = m.group(1).replace("the ", "", 1)
        target = target.replace("web", "").strip()
        if target in APPS:
            app = APPS[target]
            if "url" in app:
                return f"Opening {target}.", {"type": "url", "value": app["url"]}
            key = {"Windows": "win", "Darwin": "mac", "Linux": "linux"}.get(SYSTEM, "linux")
            return f"Opening {target}.", {"type": "app", "value": app.get(key, [])}
        return f"Opening {target}.", {"type": "app-guess", "value": target}

    m = re.match(r"^search for (.+)$|^search (.+)$|^google (.+)$", t)
    if m:
        q = next(g for g in m.groups() if g)
        return f"Searching for {q}.", {"type": "url", "value": f"https://www.google.com/search?q={quote(q)}"}

    m = re.match(r"^play (.+?)(?: on youtube)?$", t)
    if m:
        q = m.group(1)
        return f"Playing {q} on YouTube.", {"type": "url", "value": f"https://www.youtube.com/results?search_query={quote(q)}"}

    m = re.match(r"^weather(?: in| for)? ?(.*)$", t)
    if m:
        return "Checking the weather.", {"type": "weather", "city": m.group(1)}

    if t in ("forecast", "the forecast", "week's weather", "weekend weather"):
        return "Here's the forecast.", {"type": "weather", "city": ""}

    if t in ("what time is it", "time", "tell me the time"):
        return f"It's {datetime.now().strftime('%I:%M %p')}.", {"type": "speak"}

    if t in ("what's the date", "what is the date", "what day is it"):
        return f"Today is {datetime.now():%A, %B %d, %Y}.", {"type": "speak"}

    m = re.match(r"^(?:who is|what is|what are|tell me about) (.+)$", t)
    if m:
        return "Let me look that up.", {"type": "websearch", "query": m.group(1)}

    m = re.match(r"^(?:add|schedule|put) (.+)$", t)
    if m:
        rest = re.sub(r"\b(?:to|on) my calendar\b", "", m.group(1)).strip()
        when = calendar_store.parse_when(rest)
        if when:
            title = calendar_store.split_title(rest)
            return (f"Added “{title}” for {when:%A at %I:%M %p}.",
                    {"type": "calendar", "op": "add", "title": title,
                     "when": when.isoformat()})

    if t in ("what s on my calendar", "my schedule", "my calendar",
             "what s on my calendar today", "what's on my calendar"):
        return "Here's your schedule.", {"type": "calendar", "op": "list"}

    if t in ("export my calendar", "export calendar", "share my calendar"):
        return "Exporting your calendar.", {"type": "calendar", "op": "export"}

    if t in ("turn on the lights", "lights on", "light on", "switch on the lights"):
        return "Lights on.", {"type": "lights", "op": "on"}
    if t in ("turn off the lights", "lights off", "light off", "switch off the lights"):
        return "Lights off.", {"type": "lights", "op": "off"}
    m = re.match(r"^set (?:the )?lights? to (\d{1,3})(?: percent)?$", t)
    if m:
        return f"Setting lights to {m.group(1)}%.", {"type": "lights", "op": "set", "value": int(m.group(1))}
    m = re.match(r"^(?:set |make |turn )?(?:the )?lights? "
                 r"(red|orange|yellow|green|cyan|blue|purple|pink|warm|white|cool)$", t)
    if m:
        return f"Setting lights to {m.group(1)}.", {"type": "lights", "op": "color", "color": m.group(1)}

    if t in ("volume up", "louder"):
        return "Volume up.", {"type": "volume", "op": "up"}
    if t in ("volume down", "quieter"):
        return "Volume down.", {"type": "volume", "op": "down"}
    if t in ("mute", "unmute"):
        return "Toggling mute.", {"type": "volume", "op": "mute"}

    m = re.match(r"^set volume to (\d+)(?: percent)?$", t)
    if m:
        return f"Setting volume to {m.group(1)}%.", {"type": "volume", "op": "set", "value": int(m.group(1))}

    m = re.match(r"^(?:remember that|note that|remember) (.+)$", t)
    if m and memory is not None:
        # keep the user's original capitalization
        orig = re.match(r"^(?:remember that|note that|remember) (.+)$", (text or "").strip(),
                        re.IGNORECASE)
        memory.add_note((orig or m).group(1).strip())
        return "Got it — I'll remember that.", {"type": "speak"}

    if t in ("what do you remember", "your notes", "list notes"):
        if memory is not None and memory.notes:
            return "I remember: " + "; ".join(n["text"] for n in memory.notes[-5:]) + ".", {"type": "speak"}
        return "I don't have any notes yet.", {"type": "speak"}

    if t in ("stop listening", "stop listening lala", "that s all for now",
             "thats all for now", "goodbye for now", "you can sleep now", "go idle"):
        return "Okay — I'll wait for the wake word.", {"type": "end-conversation"}

    # ---- role modes ------------------------------------------------------
    if t in ("back to normal", "default mode", "switch to assistant", "normal mode"):
        return "Back to default assistant.", {"type": "role", "role": ""}
    m = re.match(r"^(?:switch to|enter|activate|use|be my|act as)(?: a| my)?\s*"
                 r"(.+?)(?:\s+mode)?$", t)
    if m:
        role = roles.normalize_role(m.group(1))
        if role:
            return f"Switching to {m.group(1)} mode.", {"type": "role", "role": role}
        if m.group(1) in ("assistant", "default", "normal"):
            return "Back to default assistant.", {"type": "role", "role": ""}
    if t in ("which mode", "current mode", "what mode"):
        return "", {"type": "role", "role": "?"}

    m = re.match(r"^research (.+)$", t)
    if m:
        return "On it — researching.", {"type": "research", "topic": m.group(1)}
    if t in ("brief me", "morning briefing", "daily briefing", "prepare my day"):
        return "", {"type": "briefing"}
    m = re.match(r"^add expense (\d+(?:\.\d+)?) for (.+)$", t)
    if m:
        return f"Recorded {float(m.group(1)):,.0f} for {m.group(2)}.", \
            {"type": "expense", "amount": float(m.group(1)), "desc": m.group(2)}
    if t in ("finance summary", "spend summary", "expenses summary"):
        return "", {"type": "finance-summary"}
    m = re.match(r"^add contact (.+?) at (.+)$", t)
    if m:
        return f"Saved {m.group(1)} @ {m.group(2)}.", \
            {"type": "contact", "name": m.group(1), "company": m.group(2)}
    if t in ("show contacts", "my contacts", "list contacts"):
        return "", {"type": "contacts"}
    m = re.match(r"^swot for (.+)$", t)
    if m:
        return "", {"type": "swot", "topic": m.group(1)}

    if t in ("user guide", "how do i use you", "how do i speak to you",
             "teach me to use you", "tutorial", "help me speak", "guide me",
             "how do i talk to you"):
        return "", {"type": "guide"}

    if t in ("flip a coin", "coin flip", "heads or tails"):
        return random.choice(["Heads!", "Tails!"]), {"type": "speak"}
    if t in ("roll a dice", "roll the dice", "roll dice"):
        return f"You rolled a {random.randint(1, 6)}.", {"type": "speak"}
    if t in ("tell me a joke", "joke", "make me laugh", "say something funny"):
        return random.choice(JOKES), {"type": "speak"}

    if t in ("lock computer", "lock the computer", "lock screen"):
        return "Locking the computer.", {"type": "power", "op": "lock"}
    if t in ("sleep computer", "sleep mode", "go to sleep"):
        return "Sleeping.", {"type": "power", "op": "sleep"}
    if t in ("shut down computer", "shutdown computer", "turn off the computer"):
        return "Shutting down — say nothing, you have a minute to cancel.", {"type": "power", "op": "shutdown", "confirm": True}
    if t in ("restart computer", "reboot computer"):
        return "Restarting — you have a minute to cancel.", {"type": "power", "op": "restart", "confirm": True}

    return None, None


# ---------------------------------------------------------------------------

def perform(action):
    """Execute a side effect. Best-effort, never raises."""
    try:
        kind = action["type"]
        if kind == "url":
            webbrowser.open(action["value"])
        elif kind == "weather":
            note = weather.summary(action.get("city", ""))
            return note or "I couldn't reach a weather service right now."
        elif kind == "websearch":
            answer = websearch.answer(action["query"])
            if answer:
                return answer
            webbrowser.open(f"https://www.google.com/search?q={quote(action['query'])}")
            return "No instant answer — I opened the search results."
        elif kind == "calendar":
            return _calendar(action)
        elif kind == "lights":
            from . import config

            _ok, msg = lights.control(config.load(), action["op"],
                                      action.get("value"), action.get("color"))
            return msg
        elif kind == "role":
            from . import config

            cur = action["role"]
            if cur == "?":
                return f"Currently in {config.load().get('role') or 'default'} mode."
            config.save({"role": cur})
            if not cur:
                return "Back to default assistant."
            nice = cur.replace("_", " ").title()
            return f"{nice} mode active — I'm your {cur.replace('_', ' ')} now."
        elif kind == "research":
            q = action["topic"]
            ans = websearch.answer(q) or ""
            webbrowser.open(f"https://scholar.google.com/scholar?q={quote(q)}")
            return (ans + " " if ans else "") + "Opened Google Scholar for deeper sources."
        elif kind == "briefing":
            from . import config

            return roles.briefing(config.load())
        elif kind == "expense":
            roles.add_expense(action["amount"], action["desc"])
            return f"Recorded {action['amount']:,.0f} for {action['desc']}."
        elif kind == "finance-summary":
            return roles.finance_summary()
        elif kind == "contact":
            roles.add_contact(action["name"], action["company"])
            return f"Saved {action['name']} @ {action['company']}."
        elif kind == "contacts":
            return roles.contact_list()
        elif kind == "swot":
            from . import config, llm

            return llm.ask(config.load(), None,
                           f"Provide a concise SWOT analysis for: {action['topic']}. "
                           "Four short bullets (S/W/O/T) and one recommendation.")
        elif kind == "guide":
            from . import config, guide

            return guide.generate(config.load())
        elif kind == "speak":
            pass
        elif kind == "app":
            _launch(action["value"])
        elif kind == "app-guess":
            _launch([action["value"], f"{action['value']}.exe"])
        elif kind == "volume":
            _volume(action)
        elif kind == "power":
            _power(action)
    except Exception as exc:  # noqa: BLE001 — voice assistant must not crash
        return f"(action failed: {exc})"
    return ""


def _calendar(action):
    if action["op"] == "add":
        events = calendar_store.load()
        events.append({"id": f"ev{len(events)}", "when": action["when"],
                       "title": action["title"]})
        calendar_store.save(events)
        return "Saved to your calendar."
    if action["op"] == "export":
        path = calendar_store.export_ics()
        return f"Exported to {path} — import it into Google or Outlook."
    pairs = calendar_store.upcoming()
    if not pairs:
        return "Your calendar is clear — nothing scheduled."
    return "Up next: " + "; ".join(calendar_store.fmt(p) for p in pairs) + "."


def _launch(candidates):
    for cand in candidates:
        if "://" in cand or cand.endswith(":"):
            webbrowser.open(cand)
            return True
        try:
            if SYSTEM == "Darwin":
                subprocess.Popen(["open", "-a", cand], start_new_session=True)
            else:
                subprocess.Popen([cand], start_new_session=True,
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except (OSError, ValueError):
            continue
    return False


def _run(cmd):
    subprocess.run(cmd, check=False, capture_output=True, timeout=8)


def _volume(action):
    op, val = action.get("op"), action.get("value", 0)
    if SYSTEM == "Darwin":
        if op == "up": _run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) + 10)"])
        elif op == "down": _run(["osascript", "-e", "set volume output volume ((output volume of (get volume settings)) - 10)"])
        elif op == "mute": _run(["osascript", "-e", "set volume output muted (not (output muted of (get volume settings)))"])
        elif op == "set": _run(["osascript", "-e", f"set volume output volume {val}"])
    elif SYSTEM == "Linux":
        tool = _first("pactl", "amixer")
        if tool == "pactl":
            arg = {"up": "+10%", "down": "-10%", "set": f"{val}%"}.get(op)
            if op == "mute": _run(["pactl", "set-sink-mute", "@DEFAULT_SINK@", "toggle"])
            elif arg: _run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", arg])
        elif tool == "amixer":
            arg = {"up": "10%+", "down": "10%-", "set": f"{val}%"}.get(op)
            if op == "mute": _run(["amixer", "-q", "sset", "Master", "toggle"])
            elif arg: _run(["amixer", "-q", "sset", "Master", arg])
    else:  # Windows: send the hardware media keys via PowerShell SendInput
        vk = {"up": "0xAF", "down": "0xAE", "mute": "0xAD"}[op if op != "set" else "down"]
        loops = 1 if op != "set" else 0
        script = (
            "Add-Type -MemberDefinition '[DllImport(\"user32.dll\")]public static extern void keybd_event(byte bVk,byte bScan,uint dwFlags,uint dwExtraInfo);' -Name K -Namespace W;"
        )
        if op == "set":
            script += f"1..50|%{{[W.K]::keybd_event(0xAE,0,0,0)}};1..{max(0, min(50, val//2))}|%{{[W.K]::keybd_event(0xAF,0,0,0)}}"
        else:
            script += f"1..{loops}|%{{[W.K]::keybd_event({vk},0,0,0)}}"
        _run(["powershell.exe", "-NoProfile", "-Command", script])


def _power(action):
    op = action["op"]
    if SYSTEM == "Windows":
        if op == "lock": _run(["rundll32.exe", "user32.dll,LockWorkStation"])
        elif op == "sleep": _run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        elif op == "shutdown": _run(["shutdown.exe", "/s", "/t", "60", "/c", "LALA shutdown — run shutdown /a to cancel"])
        elif op == "restart": _run(["shutdown.exe", "/r", "/t", "60"])
    elif SYSTEM == "Darwin":
        if op == "lock": _run(["osascript", "-e", 'tell application "System Events" to keystroke "q" using {command down, control down}'])
        elif op == "sleep": _run(["pmset", "sleepnow"])
        elif op == "shutdown": _run(["osascript", "-e", 'tell application "System Events" to shut down'])
        elif op == "restart": _run(["osascript", "-e", 'tell application "System Events" to restart'])
    else:
        if op == "lock": _run(["loginctl", "lock-session"])
        elif op == "sleep": _run(["systemctl", "suspend"])
        elif op == "shutdown": _run(["shutdown", "-h", "+1"])
        elif op == "restart": _run(["shutdown", "-r", "+1"])
