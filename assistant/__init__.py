"""
LALA / Jarvis-style Python voice assistant.

Stack (per spec):
  - Python
  - OpenAI API or local LLM (Ollama)      -> llm.py
  - Whisper speech-to-text                -> stt.py   (faster-whisper local or OpenAI API)
  - ElevenLabs or Piper text-to-speech    -> tts.py
  - Wake word via OpenWakeWord            -> wake.py  ("Hey Jarvis" default)
  - Voice conversation, Q&A, memory, app control -> orchestrator.py / router.py
"""

__version__ = "0.2.0"
