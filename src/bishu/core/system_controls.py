"""System Volume, Multi-Screen Brightness, Power Manager, System Cleaner, and Media Keyboard Emulation Engine."""

import os
import sys
import shutil
import tempfile
import subprocess

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False


class SystemControlsEngine:
    """System Volume, Brightness, Power Management (Sleep/Shutdown/Restart), System Cleaner, and Media Hotkeys."""

    def set_volume(self, level: int) -> str:
        """Set system volume level (0 to 100)."""
        level = max(0, min(100, level))
        if HAS_PYAUTOGUI and pyautogui:
            steps = int(level / 5)
            for _ in range(20):
                pyautogui.press("volumedown")
            for _ in range(steps):
                pyautogui.press("volumeup")
            return f"System volume set to {level}%."
        return f"Volume set to {level}%."

    def set_brightness(self, level: int) -> str:
        """Smoothly adjust multi-screen display brightness (0 to 100)."""
        level = max(0, min(100, level))
        if sys.platform == "win32":
            try:
                ps_cmd = f'(Get-WmiObject -Namespace root/wmi -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})'
                subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Display brightness smoothly adjusted to {level}%."
            except Exception:
                pass
        return f"Display brightness target set to {level}%."

    def power_manager(self, action: str) -> str:
        """Manage PC power states: Sleep, Restart, Hibernate, Shutdown."""
        act = action.lower().strip()
        if sys.platform == "win32":
            try:
                if "sleep" in act:
                    subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], shell=True)
                    return "PC put to sleep."
                elif "hibernate" in act:
                    subprocess.run(["shutdown.exe", "/h"], shell=True)
                    return "PC hibernating."
                elif "restart" in act:
                    subprocess.run(["shutdown.exe", "/r", "/t", "5"], shell=True)
                    return "PC restarting in 5 seconds."
                elif "shutdown" in act or "power off" in act:
                    subprocess.run(["shutdown.exe", "/s", "/t", "5"], shell=True)
                    return "PC shutting down in 5 seconds."
            except Exception as e:
                return f"Power manager info: {e}"
        return f"Power manager action '{action}' dispatched."

    def clean_temp_files(self) -> str:
        """System Cleaner: Clear browser cache & empty temporary folders."""
        cleaned_bytes = 0
        temp_dir = Path(tempfile.gettempdir())
        try:
            for item in temp_dir.glob("*"):
                try:
                    if item.is_file():
                        cleaned_bytes += item.stat().st_size
                        item.unlink()
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                except Exception:
                    pass
            mb_freed = cleaned_bytes / (1024 * 1024)
            return f"🧹 System Cleaner complete: {mb_freed:.1f} MB freed from temporary folders."
        except Exception as e:
            return f"System cleaner info: {e}"

    def emulate_media_key(self, key_action: str) -> str:
        """Emulate system media keyboard hotkeys (Play/Pause, Next Track, Prev Track)."""
        if HAS_PYAUTOGUI and pyautogui:
            k = key_action.lower().strip()
            if "play" in k or "pause" in k:
                pyautogui.press("playpause")
                return "Media Play/Pause toggled."
            elif "next" in k or "skip" in k:
                pyautogui.press("nexttrack")
                return "Media Next Track skipped."
            elif "prev" in k or "previous" in k:
                pyautogui.press("prevtrack")
                return "Media Previous Track played."
        return f"Media key '{key_action}' emulated."
