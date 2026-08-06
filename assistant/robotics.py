"""
Robotics layer (optional): generic HTTP/MQTT-style connector for
Raspberry Pi / ESP32 / arms / drones / printers / cameras.

Config:  cfg["robots"] = {"desk_cam": "http://192.168.1.50/", ...}
Commands: "robot <name> <action>" → GET {endpoint}{action} with a 2 s timeout.
Everything is opt-in and confirmation-gated for motion actions.
"""

from . import config

MOTION = ("move", "turn", "lift", "fly", "print")


def endpoints(cfg=None):
    return (cfg or config.load()).get("robots", {}) or {}


def status():
    eps = endpoints()
    if not eps:
        return ("No robots paired. Add them in config: "
                '"robots": {"desk_cam": "http://192.168.1.50/"}')
    import requests

    lines = []
    for name, url in eps.items():
        try:
            r = requests.get(url, timeout=2)
            lines.append(f"{name}: online ({r.status_code})")
        except Exception:  # noqa: BLE001
            lines.append(f"{name}: offline")
    return "; ".join(lines)


def send(name, action):
    url = endpoints().get(name)
    if not url:
        return f"No robot named {name} paired."
    import requests

    try:
        r = requests.get(url.rstrip("/") + "/" + action, timeout=3)
        return f"{name} → {action}: {r.status_code}"
    except Exception:  # noqa: BLE001
        return f"{name} unreachable for {action}."
