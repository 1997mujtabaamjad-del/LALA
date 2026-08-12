"""Voice output engine — High-Fidelity Clear Male Voice (Microsoft David), ElevenLabs, SAPI5, and PowerShell TTS with forced Male Gender Selection."""

import os
import re
import sys
import time
import json
import subprocess
import threading
import random
import urllib.request
import urllib.error
from bishu.config import VOICE_INDEX, VOICE_RATE, VOICE_VOLUME, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID


class VoiceEngine:
    """Multilingual Voice Engine configured with forced clear crisp Male Voice (Microsoft David) and ElevenLabs support."""

    def __init__(self, voice_index: int = VOICE_INDEX, rate: int = VOICE_RATE, volume: int = VOICE_VOLUME):
        self.backend = "sapi5"
        self.voice_index = voice_index
        self.rate = rate
        self.volume = volume
        self.available_voices = []
        self._init_speaker()

    def _init_speaker(self):
        """Initialize Windows SAPI5 or PowerShell System.Speech TTS Engine with forced Male Voice selection."""
        try:
            import win32com.client
            sp = win32com.client.Dispatch("SAPI.SpVoice")
            sp.Volume = self.volume
            sp.Rate = self.rate
            
            # Fetch all installed SAPI5 voices
            voices = sp.GetVoices()
            self.available_voices = [voices.Item(i).GetDescription() for i in range(voices.Count)]
            
            # Forcibly search for Microsoft David or Male Voice
            male_found = False
            for i in range(voices.Count):
                v_desc = voices.Item(i).GetDescription().lower()
                if "david" in v_desc or "male" in v_desc or "george" in v_desc or "mark" in v_desc:
                    sp.Voice = voices.Item(i)
                    self.voice_index = i
                    male_found = True
                    break

            if not male_found and 0 <= self.voice_index < len(self.available_voices):
                sp.Voice = voices.Item(self.voice_index)
                
            self.backend = "sapi5"
            print(f"[VoiceEngine] SAPI5 Speech Engine ready! Active Male Voice [{self.voice_index}]: '{self.available_voices[self.voice_index] if self.available_voices else 'Default'}'")
        except Exception as err:
            self.backend = "powershell"
            print(f"[VoiceEngine] Using Windows PowerShell System.Speech engine fallback: {err}")

    def get_time_based_greeting(self, user_title: str = "Boss") -> str:
        """Generate time-based greeting & tone based on local hour."""
        hour = time.localtime().tm_hour
        if 5 <= hour < 12:
            return f"Good morning {user_title}! How can I help you today?"
        elif 12 <= hour < 17:
            return f"Good afternoon {user_title}! What can I do for you?"
        elif 17 <= hour < 21:
            return f"Good evening {user_title}! How can I assist you?"
        else:
            return f"Hello {user_title}! What do you need help with tonight?"

    def get_available_voices(self) -> list:
        """List all available installed TTS voices on Windows."""
        if self.available_voices:
            return self.available_voices

        # PowerShell voice enumeration fallback
        if sys.platform == "win32":
            try:
                ps_cmd = 'Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).GetInstalledVoices() | ForEach-Object { $_.VoiceInfo.Name }'
                res = subprocess.check_output(["powershell", "-Command", ps_cmd], text=True, stderr=subprocess.DEVNULL)
                self.available_voices = [v.strip() for v in res.strip().split('\n') if v.strip()]
            except Exception:
                self.available_voices = ["Windows Default Voice"]
        return self.available_voices

    def set_voice_index(self, index: int) -> str:
        """Change active spoken voice by index."""
        voices = self.get_available_voices()
        if 0 <= index < len(voices):
            self.voice_index = index
            print(f"[VoiceEngine] Spoken voice updated to Index {index}: '{voices[index]}'")
            return f"Voice changed to {voices[index]}."
        return f"Invalid voice index {index}. Available indices: 0 to {len(voices)-1}."

    def set_speech_rate(self, rate: int):
        """Set speech rate (-10 to +10)."""
        self.rate = max(-10, min(10, rate))

    def _clean_text_for_speech(self, text: str) -> str:
        """Clean markdown formatting and ensure clean, plain, understandable words."""
        if not text:
            return ""

        # Remove markdown symbols and extra punctuation
        text = re.sub(r'[*_#`~]', '', text)
        text = text.replace("!", ". ").replace("?", "? ").replace(":", ". ")
        return re.sub(r'\s+', ' ', text).strip()

    def _speak_elevenlabs(self, text: str) -> bool:
        """Synthesize high-fidelity voice output via ElevenLabs API if key is configured."""
        key = os.getenv("ELEVENLABS_API_KEY", ELEVENLABS_API_KEY).strip()
        if not key:
            return False

        voice_id = os.getenv("ELEVENLABS_VOICE_ID", ELEVENLABS_VOICE_ID).strip()

        try:
            import tempfile

            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            payload = json.dumps({
                "text": text,
                "model_id": ELEVENLABS_MODEL_ID,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.8
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": key
                }
            )

            with urllib.request.urlopen(req, timeout=10) as resp:
                audio_data = resp.read()
                if audio_data and len(audio_data) > 500:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_f:
                        tmp_f.write(audio_data)
                        tmp_name = tmp_f.name

                    print(f"[VoiceEngine] Played ElevenLabs Male Voice audio ({len(audio_data)} bytes).")
                    if sys.platform == "win32":
                        ps_cmd = f'(New-Object Media.SoundPlayer "{tmp_name}").PlaySync()'
                        subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return True
        except Exception as e:
            print(f"[VoiceEngine] ElevenLabs voice info/fallback: {e}")
            
        return False

    def speak(self, text: str, voice_index: int = None):
        """Speak given text asynchronously in background daemon thread using forced Male Voice (Microsoft David)."""
        if not text:
            return

        clean_text = self._clean_text_for_speech(text)
        target_voice = self.voice_index if voice_index is None else voice_index
        print(f"[VoiceEngine] Speaking out loud in Forced Male Voice (Microsoft David): '{clean_text}'")

        def _worker(msg, v_idx):
            # 1. Try ElevenLabs API if key is set
            if self._speak_elevenlabs(msg):
                return

            # 2. Windows SAPI5 Male Voice (Microsoft David)
            if self.backend == "sapi5":
                try:
                    import pythoncom
                    pythoncom.CoInitialize()
                    try:
                        import win32com.client
                        sp = win32com.client.Dispatch("SAPI.SpVoice")
                        sp.Volume = self.volume
                        sp.Rate = self.rate
                        voices = sp.GetVoices()
                        
                        # Search for Microsoft David Male Voice
                        male_set = False
                        for i in range(voices.Count):
                            v_desc = voices.Item(i).GetDescription().lower()
                            if "david" in v_desc or "male" in v_desc or "george" in v_desc or "mark" in v_desc:
                                sp.Voice = voices.Item(i)
                                male_set = True
                                break

                        if not male_set and 0 <= v_idx < voices.Count:
                            sp.Voice = voices.Item(v_idx)

                        sp.Speak(msg, 0)  # 0 = Synchronous speech in daemon thread
                        return
                    finally:
                        pythoncom.CoUninitialize()
                except Exception as e:
                    print(f"[VoiceEngine] SAPI5 info: {e}, falling back to PowerShell...")

            # 3. Universal Windows PowerShell System.Speech Forced Male Voice Fallback
            if sys.platform == "win32":
                try:
                    ps_cmd = (
                        f'Add-Type -AssemblyName System.Speech; '
                        f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                        f'$s.Volume = {self.volume}; $s.Rate = {self.rate}; '
                        f'try {{ $s.SelectVoiceByHints([System.Speech.Synthesis.VoiceGender]::Male) }} catch {{}}; '
                        f'$s.Speak("{msg}")'
                    )
                    subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as err:
                    print(f"[VoiceEngine] PowerShell speech error: {err}")

        threading.Thread(target=_worker, args=(clean_text, target_voice), daemon=True).start()
