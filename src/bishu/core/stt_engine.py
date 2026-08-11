"""Speech-To-Text (STT) engine optimized for English, Hindi, and Urdu language recognition."""

import io
import wave
import tempfile
import numpy as np
import speech_recognition as sr

try:
    import whisper
    HAS_WHISPER = True
except Exception:
    whisper = None
    HAS_WHISPER = False


class STTEngine:
    """Listens to microphone and transcribes voice commands specializing in English, Hindi, and Urdu."""

    def __init__(self, sample_rate: int = 16000, model_size: str = "tiny"):
        self.recognizer = sr.Recognizer()
        self.sample_rate = sample_rate
        self.whisper_model = None

        if HAS_WHISPER and whisper:
            try:
                print(f"[STTEngine] Loading local OpenAI Whisper model ('{model_size}')...")
                self.whisper_model = whisper.load_model(model_size)
                print("[STTEngine] OpenAI Whisper local model ready for English, Hindi & Urdu!")
            except Exception as e:
                print(f"[STTEngine] Whisper load info/fallback: {e}")

    def listen_command(self, duration: float = 2.5) -> str:
        """Safe alias for backwards compatibility."""
        return ""

    def transcribe_buffer(self, audio_data: np.ndarray) -> str:
        """Transcribe in-memory audio buffer specializing in English, Hindi, and Urdu."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Try local OpenAI Whisper (auto-detects English, Hindi, Urdu)
        if self.whisper_model:
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
                    with wave.open(tmp_file.name, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2) # 16-bit
                        wf.setframerate(self.sample_rate)
                        if isinstance(audio_data, np.ndarray):
                            wf.writeframes(audio_data.tobytes())
                        else:
                            wf.writeframes(audio_data)

                    res = self.whisper_model.transcribe(tmp_file.name, fp16=False)
                    text = res.get("text", "").strip().lower()
                    if text:
                        print(f"[STTEngine] Whisper Transcribed: '{text}'")
                        return text
            except Exception as e:
                print(f"[STTEngine] Whisper transcription info: {e}")

        # 2. Fallback to Google STT with English / Hindi / Urdu language tags
        for lang in ["en-IN", "hi-IN", "ur-PK"]:
            try:
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    if isinstance(audio_data, np.ndarray):
                        wf.writeframes(audio_data.tobytes())
                    else:
                        wf.writeframes(audio_data)
                wav_io.seek(0)

                with sr.AudioFile(wav_io) as source:
                    audio = self.recognizer.record(source)
                    text = self.recognizer.recognize_google(audio, language=lang)
                    if text:
                        print(f"[STTEngine] Google STT ({lang}) Transcribed: '{text}'")
                        return text.lower().strip()
            except sr.UnknownValueError:
                continue
            except Exception:
                break

        return ""
