"""
Guided deployment: `python -m assistant --deploy`

  1. pick a TTS engine (ElevenLabs cloud voices, or local Piper)
  2. for ElevenLabs: validate the key, list your voices, pick one
  3. optionally install start-at-login
  4. optionally install a systemd user service for the brain server (Linux)

Non-TTY stdin falls back to environment variables (ELEVENLABS_API_KEY) so it
also works in CI-ish contexts.
"""

import os
import subprocess
import sys

from . import autostart, config, elevenlabs, tts


def _ask(prompt, default=""):
    try:
        answer = input(f"{prompt} [{default}] ").strip()
    except (EOFError, OSError):
        return default
    return answer or default


def _linux_brain_service(on=True):
    """systemd --user unit running the brain server at login."""
    unit_dir = os.path.join(os.path.expanduser("~"), ".config", "systemd", "user")
    path = os.path.join(unit_dir, "lala-brain.service")
    if not on:
        subprocess.run(["systemctl", "--user", "disable", "--now", "lala-brain"],
                       check=False, capture_output=True)
        try:
            os.unlink(path)
        except OSError:
            pass
        return path
    os.makedirs(unit_dir, exist_ok=True)
    py = sys.executable
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(path, "w", encoding="utf8") as fh:
        fh.write(
            "[Unit]\nDescription=LALA brain server\nAfter=network.target\n\n"
            "[Service]\n"
            f"WorkingDirectory={cwd}\n"
            f"ExecStart={py} -m assistant --serve\n"
            "Restart=on-failure\n\n"
            "[Install]\nWantedBy=default.target\n"
        )
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False, capture_output=True)
    subprocess.run(["systemctl", "--user", "enable", "--now", "lala-brain"],
                   check=False, capture_output=True)
    return path


def main():
    cfg = config.load()
    print("\n=== LALA deployment ===\n")

    # ---- 1. TTS engine -------------------------------------------------------
    choice = _ask("TTS engine — (e)levenlabs or (p)iper local?", "e").lower()
    if choice.startswith("e"):
        key = cfg.get("elevenlabs_api_key") or os.environ.get("ELEVENLABS_API_KEY", "")
        key = _ask("ElevenLabs API key", key[:6] + "…" if key else "") or key
        if not key or "…" in key:
            key = cfg.get("elevenlabs_api_key", "")
        try:
            elevenlabs.validate_key(key)
            print("  ✔ key valid")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✖ key rejected ({exc}) — keeping previous TTS settings.")
            return

        voices = elevenlabs.list_voices(key)
        print(f"\n  Your voices ({len(voices)}):")
        for i, v in enumerate(voices[:12], 1):
            print(f"   {i:2}. {v['name']}  [{v['category']}]")
        pick = _ask("Voice number or name", "1")
        voice = None
        if pick.isdigit() and 1 <= int(pick) <= len(voices):
            voice = voices[int(pick) - 1]
        else:
            voice = elevenlabs.find_voice(key, pick)
        if voice:
            cfg["elevenlabs_voice_id"] = voice["voice_id"]
            print(f"  ✔ voice: {voice['name']}")
        cfg["elevenlabs_api_key"] = key
        cfg["tts_provider"] = "elevenlabs"
    else:
        if not tts.piper_ready():
            print("  downloading Piper voice (~60 MB)…")
            tts.download_piper_voice(progress=lambda p: print(f"\r  {p}%", end=""))
            print()
        cfg["tts_provider"] = "piper"

    # ---- 2. LLM ----------------------------------------------------------------
    llm_choice = _ask("LLM — (o)llama local or (a) OpenAI API?", "o").lower()
    if llm_choice.startswith("a"):
        key = _ask("OpenAI API key", cfg.get("openai_api_key", ""))
        if key:
            cfg["openai_api_key"] = key
            cfg["llm_provider"] = "openai"
    else:
        cfg["llm_provider"] = "ollama"

    config.save(cfg)
    print("\n  ✔ settings saved")

    # ---- 3. auto-start ----------------------------------------------------------
    if _ask("Start LALA at login? (y/N)", "n").lower().startswith("y"):
        where = autostart.install()
        print(f"  ✔ auto-start installed: {where}")

    # ---- 4. brain service ---------------------------------------------------------
    if sys.platform.startswith("linux"):
        if _ask("Run the brain server as a systemd user service? (y/N)", "n").lower().startswith("y"):
            where = _linux_brain_service(True)
            print(f"  ✔ service installed: {where}")

    print("\nDeployment complete. Try: python -m assistant --chat\n")
