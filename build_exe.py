"""Build script to compile Laalaa into a standalone Laalaa_Arc_Reactor.exe using PyInstaller."""

import os
import subprocess
from pathlib import Path


def build_standalone_exe():
    root_dir = Path(__file__).parent
    icon_path = root_dir / "src" / "bishu" / "data" / "reactor_icon.png"
    main_script = root_dir / "src" / "bishu" / "__main__.py"

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onedir",
        "--windowed",
        f"--icon={icon_path}",
        "--name=Laalaa_Arc_Reactor",
        f"--add-data={root_dir / 'src' / 'bishu' / 'data'}:bishu/data",
        f"--paths={root_dir / 'src'}",
        str(main_script)
    ]

    print(f"[BuildExe] Compiling standalone Laalaa Arc Reactor .exe app...")
    try:
        subprocess.run(cmd, check=True)
        print(f"[BuildExe] Standalone .exe compiled to: dist/Laalaa_Arc_Reactor/Laalaa_Arc_Reactor.exe")
    except Exception as e:
        print(f"[BuildExe] PyInstaller build info: {e}")


if __name__ == "__main__":
    build_standalone_exe()
