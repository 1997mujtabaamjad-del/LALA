"""Speech-To-Text (STT) engine optimized for OpenAI Whisper & multilingual English, Hindi, and Urdu language recognition."""

import io
import os
import wave
import tempfile
import numpy as np

try:
    import speech_recognition as sr
except Exception:
    sr = None

try:
    import whisper
    HAS_WHISPER = True
except Exception:
    whisper = None
    HAS_WHISPER = False


class STTEngine:
    """Listens to microphone and transcribes voice commands specializing in English, Hindi, and Urdu using OpenAI Whisper."""

    def __init__(self, sample_rate: int = 16000, model_size: str = "tiny"):
        self.recognizer = sr.Recognizer() if sr else None
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
        """Transcribe in-memory audio buffer specializing in English, Hindi, and Urdu via OpenAI Whisper."""
        if audio_data is None or len(audio_data) == 0:
            return ""

        # 1. Try local OpenAI Whisper model
        if self.whisper_model:
            # 1a. Direct NumPy float32 array processing
            try:
                if isinstance(audio_data, np.ndarray):
                    if audio_data.dtype == np.int16:
                        audio_float = audio_data.astype(np.float32) / 32768.0
                    elif audio_data.dtype == np.float32:
                        audio_float = audio_data
                    else:
                        audio_float = audio_data.astype(np.float32)

                    res = self.whisper_model.transcribe(audio_float, fp16=False)
                    text = res.get("text", "").strip().lower()
                    if text:
                        print(f"[STTEngine] OpenAI Whisper (Direct NumPy) Transcribed: '{text}'")
                        return text
            except Exception as e:
                print(f"[STTEngine] Direct Whisper info: {e}")

            # 1b. WAV file fallback for local Whisper model
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
                        print(f"[STTEngine] OpenAI Whisper (WAV File) Transcribed: '{text}'")
                        return text
            except Exception as e:
                print(f"[STTEngine] Local Whisper WAV transcription info: {e}")

        # 2. Try OpenAI API Whisper STT if OPENAI_API_KEY environment variable is set
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if api_key:
            try:
                import openai
                client = openai.OpenAI(api_key=api_key)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp_file:
                    with wave.open(tmp_file.name, 'wb') as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(self.sample_rate)
                        if isinstance(audio_data, np.ndarray):
                            wf.writeframes(audio_data.tobytes())
                        else:
                            wf.writeframes(audio_data)

                    with open(tmp_file.name, "rb") as audio_file:
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1",
                            file=audio_file
                        )
                        text = getattr(transcript, "text", "").strip().lower()
                        if text:
                            print(f"[STTEngine] OpenAI Whisper API Transcribed: '{text}'")
                            return text
            except Exception as e:
                print(f"[STTEngine] OpenAI Whisper API info: {e}")

        # 3. Fallback to Google STT with English, Hindi, and Urdu language tags
        if self.recognizer:
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
                except Exception:
                    continue

        return ""
