"""
Start LALA at login (all three desktop OSes).

  python -m assistant --autostart on|off
"""

import os
import platform
import sys

SYSTEM = platform.system()


def _linux_paths():
    autostart = os.path.join(os.path.expanduser("~"), ".config", "autostart")
    return autostart, os.path.join(autostart, "lala-assistant.desktop")


def _mac_paths():
    agents = os.path.join(os.path.expanduser("~"), "Library", "LaunchAgents")
    return agents, os.path.join(agents, "ai.lala.assistant.plist")


def install(args=None):
    """Register auto-start. `args` overrides the launch command (list)."""
    py = sys.executable
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    launch = args or [py, "-m", "assistant"]

    if SYSTEM == "Linux":
        directory, path = _linux_paths()
        os.makedirs(directory, exist_ok=True)
        with open(path, "w", encoding="utf8") as fh:
            fh.write(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Name=LALA Assistant\n"
                f"Exec={' '.join(launch)}\n"
                f"Path={cwd}\n"
                "Terminal=false\n"
                "X-GNOME-Autostart-enabled=true\n"
            )
        return path

    if SYSTEM == "Darwin":
        directory, path = _mac_paths()
        os.makedirs(directory, exist_ok=True)
        prog = "".join(f"    <string>{a}</string>\n" for a in launch)
        with open(path, "w", encoding="utf8") as fh:
            fh.write(
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                '<plist version="1.0">\n<dict>\n'
                "  <key>Label</key><string>ai.lala.assistant</string>\n"
                "  <key>ProgramArguments</key>\n<array>\n"
                f"{prog}"
                "  </array>\n"
                f"  <key>WorkingDirectory</key><string>{cwd}</string>\n"
                "  <key>RunAtLoad</key><true/>\n"
                "</dict>\n</plist>\n"
            )
        return path

    if SYSTEM == "Windows":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        winreg.SetValueEx(key, "LALA Assistant", 0, winreg.REG_SZ, " ".join(launch))
        winreg.CloseKey(key)
        return "HKCU\\...\\Run\\LALA Assistant"

    raise RuntimeError(f"Auto-start not supported on {SYSTEM}")


def uninstall():
    if SYSTEM == "Linux":
        _, path = _linux_paths()
    elif SYSTEM == "Darwin":
        _, path = _mac_paths()
    elif SYSTEM == "Windows":
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0, winreg.KEY_SET_VALUE,
        )
        try:
            winreg.DeleteValue(key, "LALA Assistant")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    else:
        raise RuntimeError(f"Auto-start not supported on {SYSTEM}")
    try:
        os.unlink(path)
        return True
    except OSError:
        return False
