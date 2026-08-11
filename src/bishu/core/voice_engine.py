"""Voice output engine — High-Fidelity Windows SAPI5 / PowerShell System.Speech with phonetic accent normalization for crystal-clear speech clarity."""

import os
import re
import sys
import subprocess
import threading
from bishu.config import VOICE_INDEX, VOICE_RATE, VOICE_VOLUME


class VoiceEngine:
    """Multilingual English, Hindi, and Urdu Voice Engine with phonetic accent normalization for crystal-clear clarity."""

    PHONETIC_ACCENT_MAP = {
        "khairiyat": "Khair-ee-yut",
        "farmaiye": "Far-my-ay",
        "khidmat": "Khid-mut",
        "haazir": "Haa-zeer",
        "hazir": "Haa-zeer",
        "walaikum": "Wa-lay-koom",
        "assalam": "Us-sa-laam",
        "alaikum": "Ulay-koom",
        "shakhsi": "Shukh-see",
        "bilkul": "Bil-kool",
        "shukriya": "Shook-ree-ya",
        "bohot": "Bo-hut",
        "bahut": "Bo-hut",
        "accha": "Uch-chhaa",
        "achha": "Uch-chhaa",
        "kaun": "Kone",
        "kaise": "Kay-say",
        "kya": "Kyaa",
        "kiya": "Kyaa",
        "aap": "Aap",
        "aapka": "Aap-kaa",
        "aapki": "Aap-kee",
        "thik": "Theek",
        "theek": "Theek",
        "ji": "Jee",
        "haan": "Haa"
    }

    def __init__(self, voice_index: int = VOICE_INDEX, rate: int = VOICE_RATE, volume: int = VOICE_VOLUME):
        self.backend = "sapi5"
        self.voice_index = voice_index
        self.rate = rate
        self.volume = volume
        self.available_voices = []
        self._init_speaker()

    def _init_speaker(self):
        """Initialize Windows SAPI5 or PowerShell System.Speech TTS Engine."""
        try:
            import win32com.client
            sp = win32com.client.Dispatch("SAPI.SpVoice")
            sp.Volume = self.volume
            sp.Rate = self.rate
            
            # Fetch all installed SAPI5 voices
            voices = sp.GetVoices()
            self.available_voices = [voices.Item(i).GetDescription() for i in range(voices.Count)]
            
            if 0 <= self.voice_index < len(self.available_voices):
                sp.Voice = voices.Item(self.voice_index)
                
            self.backend = "sapi5"
            print(f"[VoiceEngine] SAPI5 Speech Engine ready! Active Voice [{self.voice_index}]: '{self.available_voices[self.voice_index] if self.available_voices else 'Default'}'")
        except Exception as err:
            self.backend = "powershell"
            print(f"[VoiceEngine] Using Windows PowerShell System.Speech engine fallback: {err}")

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

    def _normalize_accent_phonetics(self, text: str) -> str:
        """Normalize Roman Hindi/Urdu words for clear, natural, human-understandable TTS accent."""
        if not text:
            return ""

        # Phonetic substitution for smooth pronunciation
        for word, phonetic in self.PHONETIC_ACCENT_MAP.items():
            text = re.sub(r'\b' + re.escape(word) + r'\b', phonetic, text, flags=re.IGNORECASE)

        # Add natural comma pauses for clear speech cadence
        text = text.replace("!", "! ").replace(".", ". ").replace("?", "? ")
        return re.sub(r'\s+', ' ', text).strip()

    def speak(self, text: str, voice_index: int = None):
        """Speak given text asynchronously in background daemon thread with accent normalization."""
        if not text:
            return

        clean_text = self._normalize_accent_phonetics(text)
        target_voice = self.voice_index if voice_index is None else voice_index
        print(f"[VoiceEngine] Speaking out loud (Voice #{target_voice}, Rate {self.rate}): '{clean_text}'")

        def _worker(msg, v_idx):
            # 1. Windows SAPI5 COM Speech
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
                        if 0 <= v_idx < voices.Count:
                            sp.Voice = voices.Item(v_idx)
                        sp.Speak(msg, 0)  # 0 = Synchronous speech in daemon thread
                        return
                    finally:
                        pythoncom.CoUninitialize()
                except Exception as e:
                    print(f"[VoiceEngine] SAPI5 info: {e}, falling back to PowerShell...")

            # 2. Universal Windows PowerShell System.Speech Fallback
            if sys.platform == "win32":
                try:
                    ps_cmd = (
                        f'Add-Type -AssemblyName System.Speech; '
                        f'$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
                        f'$s.Volume = {self.volume}; $s.Rate = {self.rate}; '
                        f'$v = $s.GetInstalledVoices(); '
                        f'if ({v_idx} -lt $v.Count) {{ $s.SelectVoice($v[{v_idx}].VoiceInfo.Name) }}; '
                        f'$s.Speak("{msg}")'
                    )
                    subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception as err:
                    print(f"[VoiceEngine] PowerShell speech error: {err}")

        threading.Thread(target=_worker, args=(clean_text, target_voice), daemon=True).start()
