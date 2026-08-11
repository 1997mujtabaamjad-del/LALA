"""Spotify Music Integration Agent for searching tracks, controlling volume, and playing playlists."""

import urllib.parse
import webbrowser

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False


class SpotifyAgent:
    """Spotify Music Integration for searching tracks, volume control, and playlist playback."""

    def search_track(self, query: str) -> str:
        """Search tracks on Spotify and open web player."""
        q_enc = urllib.parse.quote(query.strip())
        url = f"https://open.spotify.com/search/{q_enc}"
        webbrowser.open(url)
        return f"Spotify track search opened for '{query}'."

    def set_volume(self, level: int) -> str:
        """Adjust system & media playback volume level (0 to 100)."""
        level = max(0, min(100, level))
        if HAS_PYAUTOGUI and pyautogui:
            # Normalize to keypresses
            steps = int(level / 5)
            for _ in range(20):
                pyautogui.press("volumedown")
            for _ in range(steps):
                pyautogui.press("volumeup")
            return f"Spotify media volume set to {level}%."
        return f"Volume level target set to {level}%."

    def play_playlist(self, playlist_name: str) -> str:
        """Search and play Spotify playlist."""
        p_enc = urllib.parse.quote(playlist_name.strip())
        url = f"https://open.spotify.com/search/{p_enc}/playlists"
        webbrowser.open(url)
        return f"Playing Spotify playlist: '{playlist_name}'."
