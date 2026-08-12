"""Compiles Laalaa into ONE SINGLE STANDALONE EXECUTABLE FILE (Laalaa.exe) using PyInstaller --onefile."""

import os
import sys
import subprocess
from pathlib import Path


def build_single_file_exe():
    root_dir = Path(__file__).parent
    icon_path = root_dir / "src" / "bishu" / "data" / "reactor_icon.png"
    main_script = root_dir / "src" / "bishu" / "__main__.py"

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",  # Bundles EVERYTHING into 1 single executable file!
        "--windowed",
        f"--icon={icon_path}",
        "--name=Laalaa",
        f"--add-data={root_dir / 'src' / 'bishu' / 'data'}:bishu/data",
        f"--paths={root_dir / 'src'}",
        str(main_script)
    ]

    print("[SingleExeBuilder] Compiling Laalaa into ONE SINGLE STANDALONE FILE (Laalaa.exe)...")
    try:
        subprocess.run(cmd, check=True)
        dist_exe = root_dir / "dist" / "Laalaa.exe"
        print(f"\n🎉 SUCCESS! One single standalone file generated at: {dist_exe}")
        return str(dist_exe)
    except Exception as e:
        print(f"[SingleExeBuilder] PyInstaller build info: {e}")
        return ""


if __name__ == "__main__":
    build_single_file_exe()
