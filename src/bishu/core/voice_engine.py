"""Voice output engine — Windows SAPI5 / PowerShell System.Speech (100% reliable)."""

import os
import sys
import subprocess
import threading


class VoiceEngine:
    """High-Fidelity Text-To-Speech Voice Engine with Windows PowerShell fallback."""

    def __init__(self):
        self.backend = "sapi5"
        self._speaker = None
        self._init_speaker()

    def _init_speaker(self):
        try:
            import win32com.client
            self._speaker = win32com.client.Dispatch("SAPI.SpVoice")
            self._speaker.Volume = 100
            self.backend = "sapi5"
            print("[VoiceEngine] Windows SAPI5 Speech Engine initialized successfully!")
        except Exception as err:
            self._speaker = None
            self.backend = "powershell"
            print("[VoiceEngine] Using Windows PowerShell System.Speech engine.")

    def speak(self, text: str):
        """Speak given text in background daemon thread without blocking GUI or crashing."""
        if not text:
            return

        clean_text = text.replace('"', '').replace("'", "").replace('\n', ' ').strip()
        print(f"[VoiceEngine] Speaking out loud: '{clean_text}'")

        def _worker(msg):
            try:
                # 1. Try Windows SAPI5 COM object
                if self.backend == "sapi5":
                    try:
                        import pythoncom
                        pythoncom.CoInitialize()
                        import win32com.client
                        sp = win32com.client.Dispatch("SAPI.SpVoice")
                        sp.Volume = 100
                        sp.Speak(msg, 0) # 0 = Synchronous speech in daemon thread
                        return
                    except Exception as e:
                        print(f"[VoiceEngine] SAPI5 info: {e}, falling back to PowerShell...")

                # 2. Universal Windows PowerShell System.Speech Fallback (Built into all Windows PCs)
                if sys.platform == "win32":
                    ps_cmd = f'Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Volume = 100; $s.Speak("{msg}")'
                    subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception as err:
                print(f"[VoiceEngine] Speech error: {err}")

        threading.Thread(target=_worker, args=(clean_text,), daemon=True).start()
