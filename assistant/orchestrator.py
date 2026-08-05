"""
Conversation state machine shared by the GUI and the terminal CLI:

  wake word (or button) -> record until silence -> Whisper STT
      -> deterministic command? run it : LLM answer (with memory)
      -> TTS -> short follow-up window for natural back-and-forth.
"""

import threading

from . import llm, mic, router, stt, tts, wake
from .memory import Memory


class Assistant:
    def __init__(self, cfg, log=None, status=None, confirm=None):
        self.cfg = cfg
        self.log = log or (lambda *a, **k: None)
        self.status = status or (lambda *a, **k: None)
        self.confirm_fn = confirm or self._stdin_confirm
        self.memory = Memory()
        self.wake = None
        self._busy = threading.Event()

    # ------------------------------------------------------------ lifecycle
    def start(self):
        if self.cfg.get("wake_enabled") and mic.available():
            self.wake = wake.WakeListener(
                self.cfg,
                on_wake=self.on_wake,
                on_status=lambda s: self.status(f"wake: {s}"),
            )
            if self.wake.start():
                self.log("system", f"Wake word armed — say “{self.cfg['wake_word'].replace('_', ' ')}”.")
            else:
                self.wake = None
                self.log("system", "Wake word unavailable (needs `pip install openwakeword` + mic). Use push-to-talk.")
        else:
            self.log("system", "Push-to-talk mode (no wake word).")

    def stop(self):
        if self.wake:
            self.wake.stop()

    # ------------------------------------------------------------ the loop
    def on_wake(self):
        threading.Thread(target=self._turn, args=(True,), daemon=True).start()

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

    def _turn(self, woke):
        if self._busy.is_set():
            return
        self._busy.set()
        if self.wake:
            self.wake.pause()
        try:
            if woke:
                mic.beep()
                self.log("system", "Yes? I'm listening…")
            self.status("listening")
            audio = mic.record_until_silence()
            self._transcribe_and_process(audio, follow_up=True)
        finally:
            self.status("idle")
            if self.wake:
                self.wake.resume()
            self._busy.clear()

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
        if action is not None:
            if action.get("confirm") and not self.confirm_fn(text):
                self._say("Okay, cancelled.", spoken)
                return "Okay, cancelled."
            side_note = router.perform(action)
            reply = response + (" " + side_note if side_note else "")
        else:
            self.status("thinking")
            if spoken and tts.resolve_provider(self.cfg) != "none":
                # Stream tokens into sentence-level TTS for minimal latency.
                reply = tts.speak_stream(llm.ask_stream(self.cfg, self.memory, text), self.cfg)
            else:
                reply = llm.ask(self.cfg, self.memory, text)

        self.memory.add("user", text)
        self.memory.add("assistant", reply)
        self._say(reply, spoken)

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
        self.log(self.cfg["name"], text)
        if not spoken:
            return

        # Barge-in: if the user starts talking over us, stop playback and
        # listen to what they say instead.
        stop = threading.Event()
        monitor = mic.BargeMonitor(stop) if mic.available() else None
        if monitor:
            monitor.start()
        tts.speak(text, self.cfg, stop_event=stop)
        barged = bool(monitor and monitor.barged)
        if monitor:
            monitor.stop()
        if barged:
            self.log("system", "(barge-in — listening)")
            self.status("listening")
            audio = mic.record_until_silence()
            try:
                next_text = stt.transcribe(audio, self.cfg)
            except Exception:  # noqa: BLE001
                next_text = ""
            if next_text:
                self.process(next_text, follow_up=False, spoken=True)
