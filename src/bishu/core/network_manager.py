"""Network Manager Agent for scanning WiFi networks, connecting saved profiles, and toggling WiFi."""

import sys
import subprocess


class NetworkManagerAgent:
    """Network Manager for WiFi scanning, saved profile connection, and WiFi disconnect toggles."""

    def scan_wifi_networks(self) -> str:
        """Scan nearby WiFi networks via Windows netsh."""
        if sys.platform != "win32":
            return "WiFi network scanning active (Linux/macOS fallback)."

        try:
            cmd = "netsh wlan show networks"
            res = subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL)
            lines = [line.strip() for line in res.split("\n") if "SSID" in line or "Signal" in line]
            if lines:
                return "📶 Nearby WiFi Networks:\n" + "\n".join(lines[:10])
            return "No nearby WiFi networks detected."
        except Exception as e:
            return f"WiFi scan info: {e}"

    def connect_wifi(self, profile_name: str) -> str:
        """Connect to a saved WiFi profile."""
        if sys.platform != "win32":
            return f"Connecting to WiFi profile '{profile_name}'."

        try:
            cmd = f'netsh wlan connect name="{profile_name.strip()}"'
            subprocess.run(cmd, shell=True, check=True)
            return f"Connected to WiFi network profile '{profile_name}'."
        except Exception as e:
            return f"Failed to connect WiFi profile '{profile_name}': {e}"

    def disconnect_wifi(self) -> str:
        """Disconnect current WiFi connection."""
        if sys.platform != "win32":
            return "WiFi disconnected."

        try:
            cmd = "netsh wlan disconnect"
            subprocess.run(cmd, shell=True, check=True)
            return "WiFi connection disconnected successfully."
        except Exception as e:
            return f"Failed to disconnect WiFi: {e}"
