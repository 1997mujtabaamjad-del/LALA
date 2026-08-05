"""
Smart lights: Philips Hue (local bridge) or Home Assistant.
Config keys: lights_provider (auto|hue|homeassistant|none), hue_ip, hue_key,
ha_url, ha_token.
"""

import requests

from . import config

# hue degrees (0-65535 scale) and kelvin for whites
COLOR_HUE = {"red": 0, "orange": 7000, "yellow": 12000, "green": 25000,
             "cyan": 32000, "blue": 46000, "purple": 50000, "pink": 56000}
COLOR_CT = {"warm": 500, "white": 370, "cool": 200}  # mireds


def build_hue_payload(op, value=None, color=None):
    """Pure Philips Hue group-action builder (unit-tested)."""
    if op == "on":
        return {"on": True}
    if op == "off":
        return {"on": False}
    if op == "set":
        bri = max(1, min(100, int(value)))
        return {"on": True, "bri": int(bri * 254 / 100)}
    if op == "color":
        if color in COLOR_CT:
            return {"on": True, "ct": COLOR_CT[color]}
        if color in COLOR_HUE:
            return {"on": True, "hue": COLOR_HUE[color], "sat": 254}
    return {"on": True}


def provider(cfg):
    pref = cfg.get("lights_provider", "auto")
    if pref in ("hue", "homeassistant", "none"):
        return pref
    if cfg.get("hue_ip") and cfg.get("hue_key"):
        return "hue"
    if cfg.get("ha_url") and cfg.get("ha_token"):
        return "homeassistant"
    return "none"


def control(cfg, op, value=None, color=None):
    """Returns (ok, message)."""
    prov = provider(cfg)
    payload = build_hue_payload(op, value, color)
    try:
        if prov == "hue":
            url = f"http://{cfg['hue_ip']}/api/{cfg['hue_key']}/groups/0/action"
            r = requests.put(url, json=payload, timeout=5)
            r.raise_for_status()
        elif prov == "homeassistant":
            service = "turn_on" if payload.get("on", True) else "turn_off"
            body = {} if service == "turn_off" else {
                "brightness": payload.get("brightness"),
            }
            if "bri" in payload:
                body = {"brightness": payload["bri"]}
            r = requests.post(
                f"{cfg['ha_url'].rstrip('/')}/api/services/light/{service}",
                headers={"Authorization": f"Bearer {cfg['ha_token']}",
                         "Content-Type": "application/json"},
                json=body, timeout=5,
            )
            r.raise_for_status()
        else:
            return False, ("No smart-light provider configured — set hue_ip/hue_key or "
                           "ha_url/ha_token in Settings.")
    except Exception as exc:  # noqa: BLE001
        return False, f"Lights unreachable: {exc}"

    label = {"on": "Lights on.", "off": "Lights off.",
             "set": f"Lights set to {value}%.",
             "color": f"Lights set to {color}."}.get(op, "Lights updated.")
    return True, label
