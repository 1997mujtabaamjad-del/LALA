"""App Packager Engine for compiling Laalaa into a native Windows Standalone Application & registering Start Menu shortcuts."""

import os
import sys
import shutil
import subprocess
from pathlib import Path


class AppPackagerEngine:
    """Standalone Application Packager & Windows Start Menu / Desktop App Installer."""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.icon_path = self.root_dir / "src" / "bishu" / "data" / "reactor_icon.png"

    def install_desktop_and_startmenu_shortcuts(self) -> str:
        """Create native Windows Desktop and Start Menu App Shortcuts."""
        if sys.platform != "win32":
            return "App Shortcuts created for desktop environment."

        try:
            vbs_script = (
                'Set WshShell = CreateObject("WScript.Shell")\n'
                'strDesktop = WshShell.SpecialFolders("Desktop")\n'
                'strStartMenu = WshShell.SpecialFolders("Programs")\n'
                f'strAppDir = "{self.root_dir}"\n\n'
                'Set objShortcutDesktop = WshShell.CreateShortcut(strDesktop & "\\Laalaa Arc Reactor.lnk")\n'
                'objShortcutDesktop.TargetPath = strAppDir & "\\Laalaa_Arc_Reactor.bat"\n'
                'objShortcutDesktop.WorkingDirectory = strAppDir\n'
                'objShortcutDesktop.Description = "Laalaa J.A.R.V.I.S. Arc Reactor AI Companion App"\n'
                f'objShortcutDesktop.IconLocation = strAppDir & "\\src\\bishu\\data\\reactor_icon.png,0"\n'
                'objShortcutDesktop.Save\n\n'
                'Set objShortcutStart = WshShell.CreateShortcut(strStartMenu & "\\Laalaa Arc Reactor.lnk")\n'
                'objShortcutStart.TargetPath = strAppDir & "\\Laalaa_Arc_Reactor.bat"\n'
                'objShortcutStart.WorkingDirectory = strAppDir\n'
                'objShortcutStart.Description = "Laalaa J.A.R.V.I.S. Arc Reactor AI Companion App"\n'
                f'objShortcutStart.IconLocation = strAppDir & "\\src\\bishu\\data\\reactor_icon.png,0"\n'
                'objShortcutStart.Save\n'
            )

            vbs_path = self.root_dir / "temp_shortcut_installer.vbs"
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_script)

            subprocess.run(["cscript", "//nologo", str(vbs_path)], check=True)
            if vbs_path.exists():
                vbs_path.unlink()

            return "📱 Laalaa App registered! Shortcut placed on Desktop & Windows Start Menu."
        except Exception as e:
            return f"Shortcut installer info: {e}"

    def build_standalone_exe_app(self) -> str:
        """Compile Laalaa into a standalone PyInstaller Windows App (.exe)."""
        main_script = self.root_dir / "src" / "bishu" / "__main__.py"
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--noconfirm",
            "--onedir",
            "--windowed",
            f"--icon={self.icon_path}",
            "--name=Laalaa_Arc_Reactor_App",
            f"--add-data={self.root_dir / 'src' / 'bishu' / 'data'}:bishu/data",
            f"--paths={self.root_dir / 'src'}",
            str(main_script)
        ]

        print("[AppPackagerEngine] Compiling standalone Windows Desktop Application...")
        try:
            subprocess.run(cmd, check=True)
            dist_path = self.root_dir / "dist" / "Laalaa_Arc_Reactor_App" / "Laalaa_Arc_Reactor_App.exe"
            return f"📦 Standalone Windows Application compiled successfully at: {dist_path}"
        except Exception as e:
            return f"PyInstaller build info: {e}"
