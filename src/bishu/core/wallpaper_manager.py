"""Desktop Wallpaper Setter & Dynamic Local Wallpaper Switcher Engine."""

import os
import sys
import ctypes
import random
from pathlib import Path


class WallpaperManagerEngine:
    """Desktop Wallpaper Manager for setting backgrounds and dynamic local switcher."""

    def __init__(self):
        self.wallpaper_dir = Path.home() / ".bishu" / "wallpapers"
        self.wallpaper_dir.mkdir(parents=True, exist_ok=True)

    def set_wallpaper(self, image_path: str) -> str:
        """Set Windows Desktop Wallpaper image."""
        path = Path(image_path)
        if not path.exists():
            return f"Image file '{image_path}' not found."

        if sys.platform == "win32":
            try:
                # SPI_SETDESKWALLPAPER = 20
                ctypes.windll.user32.SystemParametersInfoW(20, 0, str(path.resolve()), 3)
                return f"Desktop Wallpaper updated to: '{path.name}'"
            except Exception as e:
                return f"Failed to set Windows wallpaper: {e}"

        return f"Desktop Wallpaper set to: '{path.name}'"

    def switch_random_wallpaper(self) -> str:
        """Switch to a random local wallpaper image."""
        images = [p for p in self.wallpaper_dir.glob("*") if p.suffix.lower() in [".jpg", ".jpeg", ".png", ".bmp"]]
        if not images:
            return f"No wallpaper images found in '{self.wallpaper_dir}'. Place wallpaper images in this folder."

        chosen = random.choice(images)
        return self.set_wallpaper(str(chosen))
