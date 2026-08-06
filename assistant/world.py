"""
World model — live sensors so LALA knows your context:
location · weather · calendar · battery · network · devices (arp/HA) ·
open windows · running apps · active downloads.
Stdlib/OS-tool fallbacks everywhere (tasklist / pmset / sysfs / wmctrl / arp);
psutil & Home Assistant upgrade it when present. Never crashes.
"""

import socket
import subprocess
import sys

from . import calendar_store, config, weather

PLATFORM = {"win32": "win", "darwin": "mac"}.get(sys.platform, "linux")


def _run(cmd):
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=6, text=True,
                           shell=isinstance(cmd, str))
        return r.stdout if r.returncode == 0 else ""
    except Exception:  # noqa: BLE001
        return ""


def _battery():
    try:
        import psutil

        b = psutil.sensors_battery()
        return f"{int(b.percent)}%{' charging' if b.power_plugged else ''}" if b else "n/a"
    except Exception:  # noqa: BLE001
        pass
    if PLATFORM == "mac":
        for line in _run("pmset -g batt").splitlines():
            if "%" in line:
                return line.split(";")[0].strip().split("\t")[-1]
        return "unknown"
    if PLATFORM == "linux":
        for b in ("/sys/class/power_supply/BAT0/capacity",
                  "/sys/class/power_supply/BAT1/capacity"):
            try:
                with open(b, encoding="utf8") as fh:
                    return fh.read().strip() + "%"
            except OSError:
                continue
        return "unknown"
    for line in _run("WMIC PATH Win32_Battery Get EstimatedChargeRemaining /FORMAT:LIST").splitlines():
        if "=" in line:
            return line.split("=")[-1].strip() + "%"
    return "unknown"


def _top_processes(n=5):
    try:
        import psutil

        procs = sorted(psutil.process_iter(["name", "cpu_percent"]),
                       key=lambda p: p.info["cpu_percent"] or 0, reverse=True)
        return [p.info["name"] for p in procs[:n]]
    except Exception:  # noqa: BLE001
        pass
    if PLATFORM == "win":
        names = []
        for line in _run("tasklist /FO CSV /NH").splitlines():
            p = line.split('","')
            if p:
                names.append(p[0].lstrip('"'))
            if len(names) >= n:
                break
        return names
    return [l.strip() for l in _run("ps -Ao comm= -r").splitlines()[:n] if l.strip()]


def _open_windows():
    if PLATFORM == "win":
        ps = ("Get-Process | Where-Object {$_.MainWindowTitle} | "
              "Select-Object -First 6 -ExpandProperty MainWindowTitle")
        return [l.strip() for l in
                _run(["powershell", "-NoProfile", "-Command", ps]).splitlines()
                if l.strip()]
    if PLATFORM == "mac":
        out = _run(['osascript', '-e',
                    'tell application "System Events" to get name of '
                    'every process whose visible is true'])
        return [x.strip() for x in out.split(",")[:6] if x.strip()]
    out = _run("wmctrl -l") or _run("xdotool search --onlyvisible --name . getwindowname %@")
    return [l.split(None, 3)[-1] for l in out.splitlines()[:6] if l.strip()]


def _online():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2).close()
        return "online"
    except OSError:
        return "offline"


def _devices(cfg):
    if cfg.get("ha_url") and cfg.get("ha_token"):
        try:
            import requests

            r = requests.get(cfg["ha_url"].rstrip("/") + "/api/states",
                             headers={"Authorization": f"Bearer {cfg['ha_token']}"},
                             timeout=3)
            states = r.json()
            return f"{len([s for s in states if s.get('state') not in ('unavailable', 'unknown')])} Home Assistant entities"
        except Exception:  # noqa: BLE001
            return "HA unreachable"
    entries = [l for l in _run("arp -a").splitlines()
               if " " in l and "incomplete" not in l]
    return f"{len(entries)} devices on your network" if entries else "no IoT hub / device list"


def snapshot(cfg=None):
    cfg = cfg or config.load()
    return {
        "network": _online(),
        "battery": _battery(),
        "weather": (weather.summary("") or "unknown")[:140],
        "calendar": calendar_store.upcoming(3),
        "top_processes": _top_processes(),
        "open_windows": _open_windows(),
        "devices": _devices(cfg),
        "location": cfg.get("home_city", "auto (IP)"),
    }


def status_line(s):
    parts = [f"network {s['network']}", f"battery {s['battery']}"]
    if s.get("open_windows"):
        parts.append("front window: " + s["open_windows"][0])
    elif s.get("top_processes"):
        parts.append("top app: " + (s["top_processes"][0] or "?"))
    parts.append(f"devices: {s['devices']}")
    n = len(s["calendar"])
    parts.append(f"{n} upcoming event{'s' if n != 1 else ''}")
    return "; ".join(parts) + f". {s['weather']}"
