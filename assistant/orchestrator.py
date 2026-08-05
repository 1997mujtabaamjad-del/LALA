"""
Conversation state machine shared by the GUI and the terminal CLI:

  wake word (or button) -> record until silence -> Whisper STT
      -> deterministic command? run it : LLM answer (with memory)
      -> TTS -> short follow-up window for natural back-and-forth.
"""

import threading
import time

from . import config, llm, mic, router, stt, tools, tts, vad, wake
from .memory import Memory
from .pipeline import Pipeline


class Assistant:
    def __init__(self, cfg, log=None, status=None, confirm=None):
        self.cfg = cfg
        self.log = log or (lambda *a, **k: None)
        self.status = status or (lambda *a, **k: None)
        self.confirm_fn = confirm or self._stdin_confirm
        self.memory = Memory()
        self._last_action = None
        # The whole loop lives inside the pipeline now; we only plug in
        # thinking (router + LLM + memory) and the end-of-conversation flag.
        self.pipeline = Pipeline(
            cfg, log=self.log, status=self.status,
            think=self.process,
            end_check=lambda: self._last_action == "end-conversation",
        )

    # ------------------------------------------------------------ lifecycle
    def start(self):
        if not self.pipeline.start():
            self.log("system",
                     "Wake word unavailable (needs mic + vosk/openwakeword). "
                     "Use push-to-talk / the GUI / --chat.")

    def stop(self):
        self.pipeline.stop()

    # ------------------------------------------------------------ the loop
    def push_to_talk(self):
        """Blocking-style entry for the PTT button / CLI: record then process."""
        threading.Thread(target=self._ptt, daemon=True).start()

    def _ptt(self):
        if not mic.available():
            self.log("system", "No microphone available.")
            return
        self.log("system", "Listening…")
        self.status("listening")
        audio = mic.record_until_silence()
        self._transcribe_and_process(audio)

    def _transcribe_and_process(self, audio, follow_up=False):
        if audio is None or len(audio) < 1600:
            return
        self.status("thinking")
        try:
            text = stt.transcribe(audio, self.cfg)
        except Exception as exc:  # noqa: BLE001
            self.log("system", f"STT error: {exc}")
            return
        if not text:
            return
        self.process(text, follow_up=follow_up)

    # ------------------------------------------------------------ core
    def process(self, text, follow_up=False, spoken=True):
        """Handle one user utterance (voice or typed). Returns the reply."""
        self.log("you", text)

        response, action = router.handle(text, self.memory)
        self._last_action = action["type"] if action else None
        if action is not None:
            if action.get("confirm") and not self.confirm_fn(text):
                self._say("Okay, cancelled.", spoken)
                return "Okay, cancelled."
            side_note = router.perform(action)
            reply = (response + (" " + side_note if side_note else "")).strip()
        else:
            self.status("thinking")
            provider = llm.resolve_provider(self.cfg)
            interruption = None
            can_speak = spoken and tts.resolve_provider(self.cfg) != "none"
            if provider in ("openai", "ollama"):
                # Agentic + streaming: tool rounds run silently, final-answer
                # tokens flow straight into sentence-level TTS while the model
                # is still generating. Barge-in cancels generation + playback
                # and captures the interruption as a new cycle.
                if can_speak:
                    interruption, reply = self.pipeline.speak_tokens(
                        lambda stop: tools.chat_with_tools_stream(
                            self.cfg, self.memory, text, stop_event=stop))
                    spoken = False
                else:
                    reply = "".join(tools.chat_with_tools_stream(
                        self.cfg, self.memory, text))
            elif can_speak:
                # Stream tokens into sentence-level TTS for minimal latency.
                interruption, reply = self.pipeline.speak_tokens(
                    lambda stop: llm.ask_stream(
                        self.cfg, self.memory, text, stop_event=stop))
                spoken = False
            else:
                reply = llm.ask(self.cfg, self.memory, text)

        self.memory.add("user", text)
        self.memory.add("assistant", reply)
        self._say(reply, spoken)

        if interruption:
            # The user barged in: their interruption is the next utterance.
            self.process(interruption, follow_up=False, spoken=True)
            return reply

        if follow_up and mic.available():
            # Conversational follow-up window: no wake word needed.
            self.log("system", "(listening for a follow-up…)")
            audio = mic.record_until_silence(max_seconds=4.0, silence_seconds=0.8)
            if audio is not None and len(audio) >= 1600:
                try:
                    next_text = stt.transcribe(audio, self.cfg)
                except Exception:  # noqa: BLE001
                    next_text = ""
                if next_text:
                    self.process(next_text, follow_up=True, spoken=spoken)
        return reply

    def _stdin_confirm(self, text):
        """Default confirmation prompt (terminal)."""
        try:
            answer = input(f'Confirm “{text}”? [y/N] ')
            return answer.strip().lower() in ("y", "yes", "confirm")
        except (EOFError, OSError):
            return False

    def _say(self, text, spoken=True):
        # TTS with barge-in lives in the pipeline; an interruption becomes
        # the next utterance.
        interruption = self.pipeline.speak(text, spoken=spoken)
        if interruption:
            self.process(interruption, follow_up=False, spoken=True)
