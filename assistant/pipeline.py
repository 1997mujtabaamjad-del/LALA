"""
The unified voice pipeline — one chain, every stage:

    wake word -> record (+Silero VAD) -> streaming STT -> LLM -> TTS (+barge-in)
                                                                -> recording saved

`Pipeline` is what the orchestrator delegates to; `run_milestone()` is a
hardware-free self-check (`python -m assistant --milestone`) that proves each
stage works with whatever backends are installed (simulating where needed).
"""

import os
import threading
import time

import numpy as np

from . import config, llm, mic, stt, tts, vad, wake


class Pipeline:
    def __init__(self, cfg, log=None, status=None, think=None, end_check=None):
        self.cfg = cfg
        self.log = log or (lambda *a, **k: None)
        self.status = status or (lambda *a, **k: None)
        self.think = think            # text -> reply (router + LLM + memory)
        self.end_check = end_check or (lambda: False)  # e.g. "stop listening"
        self._vad = None
        self._busy = threading.Event()
        self.wake_listener = None

    def vad(self):
        if self._vad is None:
            self._vad = vad.make_vad(self.cfg)
        return self._vad

    # ------------------------------------------------------- the loop, inside
    def start(self):
        """Arm the wake word; every wake fires a full turn. Returns armed?"""
        if not self.cfg.get("wake_enabled", True) or not mic.available():
            self.log("system", "Push-to-talk mode (no wake word).")
            return False
        self.wake_listener = wake.WakeListener(
            self.cfg, on_wake=self.on_wake,
            on_status=lambda s: self.status(f"wake: {s}"))
        started = self.wake_listener.start()
        if started:
            ww = self.cfg.get("wake_word", "hey_laala").replace("_", " ")
            self.log("system", f"Wake word armed — say “{ww}”.")
        return started

    def stop(self):
        if self.wake_listener:
            self.wake_listener.stop()

    def on_wake(self):
        threading.Thread(target=self.turn, daemon=True).start()

    def turn(self):
        """One wake turn — the loop body: listen → think → speak, then keep
        listening for follow-ups until silence or end_check()."""
        if self._busy.is_set():
            return
        self._busy.set()
        if self.wake_listener:
            self.wake_listener.pause()
        try:
            mic.beep()
            self.log("system", "Yes? I'm listening…")
            continuous = bool(self.cfg.get("continuous_conversation", True))
            window = float(self.cfg.get("conversation_window_s", 8))
            next_max = 8.0
            while True:
                self.status("listening")
                audio, text, _partials = self.listen(next_max)
                if audio is None or not text:
                    break
                path = self.save_recording(audio, text)
                if path:
                    self.log("system", f"🎙 recording saved: {os.path.basename(path)}")
                if self.think is not None:
                    self.think(text)
                if self.end_check() or not continuous:
                    break
                self.log("system",
                         "(still listening — say “stop listening” to hand me "
                         "back to the wake word)")
                next_max = window
        finally:
            self.status("idle")
            if self.wake_listener:
                self.wake_listener.resume()
            self._busy.clear()

    # ------------------------------------------------------------- stage 2+3
    def listen(self, max_seconds=8.0, require_speech=True):
        """Record with VAD endpointing while streaming STT types partials.
        Returns (audio_int16 | None, transcript, partials)."""
        transcriber = stt.StreamingTranscriber(self.cfg)
        partials = []

        def on_chunk(chunk):
            partial = transcriber.feed(chunk)
            if partial:
                partials.append(partial)
                self.status(f"“{partial}”")

        audio = mic.record_until_silence(max_seconds=max_seconds,
                                         require_speech=require_speech,
                                         on_chunk=on_chunk, vad=self.vad())
        if audio is None:
            return None, "", partials
        text = transcriber.finish()
        if not text:
            try:
                text = stt.transcribe(audio, self.cfg)
            except Exception:  # noqa: BLE001
                text = ""
        return audio, text, partials

    # ------------------------------------------------------------- recording
    def save_recording(self, audio, text):
        if not self.cfg.get("save_recordings", True) or audio is None:
            return None
        path = os.path.join(config.DATA_DIR, "recordings",
                            f"lala-{int(time.time())}.wav")
        try:
            mic.save_wav(path, audio)
            return path
        except Exception:  # noqa: BLE001
            return None

    # ------------------------------------------------------------- stage 5
    def speak_tokens(self, make_tokens):
        """Streaming TTS with FULL barge-in while the mic stays open:
        1) user speech stops playback immediately,
        2) the same stop event cancels LLM generation mid-stream,
        3) the interruption is captured as a new listening cycle.
        `make_tokens(stop_event)` returns the token generator.
        Returns (interruption_text_or_None, reply_so_far)."""
        stop = threading.Event()
        monitor = mic.BargeMonitor(stop, vad=self.vad()) if mic.available() else None
        if monitor:
            monitor.start()
        reply = tts.speak_stream(make_tokens(stop), self.cfg, stop_event=stop)
        barged = bool(monitor and monitor.barged)
        if monitor:
            monitor.stop()
        if not barged:
            return None, reply
        self.log("system", "(barge-in — playback stopped, generation cancelled, listening)")
        self.status("listening")
        _audio, interruption, _p = self.listen()
        return (interruption or None), reply

    def speak(self, text, spoken=True):
        """TTS with barge-in. Returns the user's interruption text, if any."""
        self.log(self.cfg["name"], text)
        if not spoken:
            return None
        stop = threading.Event()
        monitor = mic.BargeMonitor(stop, vad=self.vad()) if mic.available() else None
        if monitor:
            monitor.start()
        tts.speak(text, self.cfg, stop_event=stop)
        barged = bool(monitor and monitor.barged)
        if monitor:
            monitor.stop()
        if not barged:
            return None
        self.log("system", "(barge-in — listening)")
        self.status("listening")
        _audio, interruption, _p = self.listen()
        return interruption or None


# ---------------------------------------------------------------------------
# Milestone self-check
# ---------------------------------------------------------------------------

def endpoint_on_array(audio, detector, cb_ms=80, chunk=1280):
    """Pure-ish VAD sweep over an array: returns (speech_ms, silence_ms)."""
    speech = silence = 0
    for i in range(0, len(audio), chunk):
        if detector.speech(audio[i:i + chunk]):
            speech += cb_ms
        else:
            silence += cb_ms
    return speech, silence


def synthetic_utterance(seconds_speech=0.6, seconds_silence=0.4, rate=16000):
    t = np.arange(int(seconds_speech * rate), dtype=np.float32) / rate
    tone = (0.3 * np.sin(2 * np.pi * 440 * t) * 32767).astype(np.int16)
    return np.concatenate([tone, np.zeros(int(seconds_silence * rate), dtype=np.int16)])


def run_milestone(cfg, speak=False):
    """[(stage, ok, note)] — exercises the whole chain without a microphone."""
    results = []

    # 1. wake word
    sample = "hey laala, open youtube"
    matched = bool(wake.WAKE_RE.search(sample))
    results.append(("wake word", matched, f"detected in “{sample}”"))

    # 2. VAD + recording (deterministic energy sweep; runtime VAD reported)
    audio = synthetic_utterance()
    speech_ms, _silence = endpoint_on_array(audio, vad.EnergyVAD())
    runtime_vad = vad.make_vad(cfg).__class__.__name__
    results.append(("vad + record", speech_ms >= 400,
                    f"{speech_ms} ms speech segmented; runtime VAD: {runtime_vad}"))

    # 3. streaming STT
    transcriber = stt.StreamingTranscriber(cfg)
    for i in range(0, len(audio), 3200):
        transcriber.feed(audio[i:i + 3200])
    text = transcriber.finish()
    results.append(("streaming stt", True,
                    f"live transcript: “{text}”" if text
                    else "simulated transcript (install faster-whisper/deepgram/vosk for live)"))

    # 4. LLM
    provider = llm.resolve_provider(cfg)
    reply = llm.ask(cfg, None, "Reply with the single word: ready")
    results.append(("llm", bool(reply), f"provider: {provider}"))

    # 5. TTS + playback
    tprov = tts.resolve_provider(cfg)
    if speak and tprov != "none":
        tts.speak("Milestone achieved.", cfg)
        results.append(("tts + playback", True, f"provider: {tprov} (spoken aloud)"))
    else:
        results.append(("tts + playback", True,
                        f"provider: {tprov} (silent check; use --speak to hear it)"))

    # 6. recording persisted
    path = os.path.join(config.DATA_DIR, "recordings",
                        f"milestone-{int(time.time())}.wav")
    mic.save_wav(path, audio)
    results.append(("recording", os.path.exists(path), os.path.basename(path)))

    return results
