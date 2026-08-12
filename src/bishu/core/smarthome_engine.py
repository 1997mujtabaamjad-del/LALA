"""Smart Home IoT integration engine supporting Home Assistant API & local smart device controls."""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path


class SmartHomeEngine:
    """Smart Home Manager for controlling lights, fans, AC, smart plugs, and IoT switches."""

    def __init__(self, ha_url: str = "http://localhost:8123", ha_token: str = ""):
        self.ha_url = os.getenv("HOME_ASSISTANT_URL", ha_url).rstrip("/")
        self.ha_token = os.getenv("HOME_ASSISTANT_TOKEN", ha_token)
        self.state_file = Path.home() / ".bishu" / "smarthome_state.json"
        self.state = {
            "living_room_light": "off",
            "bedroom_light": "off",
            "ceiling_fan": "off",
            "air_conditioner": "off",
            "ac_temperature": 24,
            "smart_plug": "off"
        }
        self.load_state()

    def load_state(self):
        """Load local smart home device state from JSON cache."""
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.state.update(data)
            except Exception as e:
                print(f"[SmartHomeEngine] Load state info: {e}")

    def save_state(self):
        """Save local smart home device state to JSON cache."""
        try:
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            print(f"[SmartHomeEngine] Save state info: {e}")

    def process_voice_command(self, cmd: str) -> tuple:
        """Process multilingual smart home voice commands (English, Hindi, Urdu)."""
        cmd = cmd.lower().strip()

        # 1. Lights ON / OFF
        if any(w in cmd for w in ["light on", "lights on", "bijli chalao", "roshni chalao", "light chalao"]):
            self.state["living_room_light"] = "on"
            self.state["bedroom_light"] = "on"
            self.save_state()
            self._call_home_assistant("light", "turn_on")
            return True, "Lights on kar di hain."

        elif any(w in cmd for w in ["light off", "lights off", "light band", "lights band", "roshni band"]):
            self.state["living_room_light"] = "off"
            self.state["bedroom_light"] = "off"
            self.save_state()
            self._call_home_assistant("light", "turn_off")
            return True, "Lights band kar di hain."

        # 2. Fan ON / OFF
        elif any(w in cmd for w in ["fan on", "pankha on", "pankha chalao", "turn on fan"]):
            self.state["ceiling_fan"] = "on"
            self.save_state()
            self._call_home_assistant("fan", "turn_on")
            return True, "Pankha on kar diya hai."

        elif any(w in cmd for w in ["fan off", "pankha off", "pankha band", "turn off fan"]):
            self.state["ceiling_fan"] = "off"
            self.save_state()
            self._call_home_assistant("fan", "turn_off")
            return True, "Pankha band kar diya hai."

        # 3. AC ON / OFF & Temperature
        elif any(w in cmd for w in ["ac on", "air conditioner on", "ac chalao"]):
            self.state["air_conditioner"] = "on"
            self.save_state()
            self._call_home_assistant("climate", "turn_on")
            return True, f"AC on kar diya hai. Current temperature {self.state['ac_temperature']}°C hai."

        elif any(w in cmd for w in ["ac off", "air conditioner off", "ac band"]):
            self.state["air_conditioner"] = "off"
            self.save_state()
            self._call_home_assistant("climate", "turn_off")
            return True, "AC band kar diya hai."

        elif "temperature" in cmd or "temp" in cmd or "ac " in cmd:
            import re
            numbers = re.findall(r'\d+', cmd)
            if numbers:
                temp = int(numbers[0])
                if 16 <= temp <= 30:
                    self.state["ac_temperature"] = temp
                    self.save_state()
                    return True, f"AC temperature {temp}°C par set kar diya hai."

        # 4. Smart Plug / Socket
        elif any(w in cmd for w in ["plug on", "socket on", "swatich on"]):
            self.state["smart_plug"] = "on"
            self.save_state()
            return True, "Smart plug switch on kar diya hai."

        elif any(w in cmd for w in ["plug off", "socket off", "switch off"]):
            self.state["smart_plug"] = "off"
            self.save_state()
            return True, "Smart plug switch off kar diya hai."

        # 5. Smart Home Device Status
        elif any(w in cmd for w in ["smart home status", "ghar ka status", "device status", "home status"]):
            status_summary = (
                f"Smart Home Status: Lights: {self.state['living_room_light']}, "
                f"Fan: {self.state['ceiling_fan']}, AC: {self.state['air_conditioner']} "
                f"({self.state['ac_temperature']}°C), Plug: {self.state['smart_plug']}."
            )
            return True, status_summary

        return False, "Not a smart home command."

    def _call_home_assistant(self, domain: str, service: str, entity_id: str = None):
        """Call Home Assistant REST API if server is reachable."""
        if not self.ha_token:
            return
        try:
            url = f"{self.ha_url}/api/services/{domain}/{service}"
            payload = json.dumps({"entity_id": entity_id or f"{domain}.all"}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bearer {self.ha_token}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                pass
        except Exception:
            pass
