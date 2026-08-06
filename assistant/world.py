"""
World model — live sensors so LALA knows your context:
location · weather · calendar · battery · processes · network · devices.
Every sensor is optional; missing ones report "unknown", never crash.
"""

import socket

from . import calendar_store, config, weather


def _battery():
    try:
        import psutil

        b = psutil.sensors_battery()
        return f"{int(b.percent)}%{' charging' if b.power_plugged else ''}" if b else "n/a"
    except Exception:  # noqa: BLE001
        return "unknown"


def _top_processes(n=5):
    try:
        import psutil

        procs = sorted(psutil.process_iter(["name", "cpu_percent"]),
                       key=lambda p: p.info["cpu_percent"] or 0, reverse=True)
        return [p.info["name"] for p in procs[:n]]
    except Exception:  # noqa: BLE001
        return []


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
    return "no IoT hub configured"


def snapshot(cfg=None):
    cfg = cfg or config.load()
    return {
        "network": _online(),
        "battery": _battery(),
        "weather": (weather.summary("") or "unknown")[:140],
        "calendar": calendar_store.upcoming(3),
        "top_processes": _top_processes(),
        "devices": _devices(cfg),
        "location": cfg.get("home_city", "auto (IP)"),
    }


def status_line(s):
    parts = [f"network {s['network']}", f"battery {s['battery']}"]
    if s["top_processes"]:
        parts.append("top app: " + (s["top_processes"][0] or "?"))
    parts.append(f"devices: {s['devices']}")
    n = len(s["calendar"])
    parts.append(f"{n} upcoming event{'s' if n != 1 else ''}")
    return "; ".join(parts) + f". {s['weather']}"
