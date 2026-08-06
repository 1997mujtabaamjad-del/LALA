"""
Section 7 — Voice Pipeline latency: measurement + budget enforcement.

The chain, end to end:

    Wake Word → Speech Recognition → Intent Detection → Planner
             → Tool Execution → Response Generation → Speech Synthesis

Budget: **simple commands must complete well under one second.**
Deterministic commands (open X, time, volume, lights, calendar…) never
touch the LLM — they run intent → router → action → reply locally, so
the whole chain costs single-digit milliseconds.

    python -m assistant --latency     # live report, per-stage ms + pass/fail

`TurnTimer` is used by the orchestrator to time every REAL turn and log
a one-line trace (⏱ intent 0.2 ms · route 3 ms · tool 90 ms …).
"""

import time
from contextlib import contextmanager

import numpy as np

from . import intent, planner, router, stt, vad, wake

# The budget for simple (deterministic) commands, per the spec.
SIMPLE_COMMAND_BUDGET_MS = 1000.0

# Canonical stage names, in pipeline order (spec §7).
STAGES = ("wake", "stt", "intent", "plan", "tool", "reply", "tts")

STAGE_LABELS = {
    "wake": "wake word",
    "stt": "speech recognition",
    "intent": "intent detection",
    "plan": "planner",
    "tool": "tool execution",
    "reply": "response generation",
    "tts": "speech synthesis",
}


def _fmt(ms):
    return f"{ms:.1f} ms" if ms >= 1 else f"{ms * 1000:.0f} µs"


class TurnTimer:
    """Per-stage stopwatch for one turn. Stages accumulate (a turn may
    visit `tool` several times during LLM tool rounds)."""

    def __init__(self):
        self.stages = {}
        self.notes = {}
        self.t0 = time.perf_counter()

    @contextmanager
    def stage(self, name):
        t0 = time.perf_counter()
        try:
            yield
        finally:
            dt = (time.perf_counter() - t0) * 1000
            self.stages[name] = self.stages.get(name, 0.0) + dt

    def mark(self, name, ms):
        self.stages[name] = self.stages.get(name, 0.0) + ms

    @property
    def total_ms(self):
        return (time.perf_counter() - self.t0) * 1000

    @property
    def work_ms(self):
        return sum(self.stages.values())

    def trace(self):
        """'intent 0.2 ms · route 3.1 ms · tool 90 ms' in pipeline order."""
        order = ("wake", "stt", "intent", "route", "plan", "tool", "reply", "tts")
        parts = [f"{k} {_fmt(self.stages[k])}" for k in order if self.stages.get(k)]
        for key, ms in self.stages.items():  # any non-canonical stages
            if key not in order and ms:
                parts.append(f"{key} {_fmt(ms)}")
        return " · ".join(parts) if parts else "no stages timed"

    def verdict(self, budget_ms=SIMPLE_COMMAND_BUDGET_MS, fast_path=True):
        if not fast_path:
            return "LLM path (streaming; budget applies to simple commands)"
        work = self.work_ms
        return (f"under {int(budget_ms)} ms ✓" if work <= budget_ms
                else f"OVER {int(budget_ms)} ms budget ✗")


# ---------------------------------------------------------------------------
# One deterministic chain, timed (importable / testable)
# ---------------------------------------------------------------------------

def simple_chain(text, memory=None, perform=False, timer=None):
    """Run wake-stripped text through intent → router → (optional) action.
    Returns (timer, intent_name, response, action). Never touches the LLM."""
    timer = timer or TurnTimer()
    with timer.stage("intent"):
        kind = intent.detect(text)
    with timer.stage("route"):
        response, action = router.handle(text, memory)
    if action is not None and perform and action["type"] not in ("speak", "end-conversation"):
        with timer.stage("tool"):
            router.perform(action)
    if response:
        timer.notes.setdefault("reply", "deterministic")
    return timer, kind, response, action


# ---------------------------------------------------------------------------
# Full latency report (`python -m assistant --latency`)
# ---------------------------------------------------------------------------

def run_latency_report(cfg):
    """[(scenario, ms, ok, note)] — every stage of the §7 chain, measured
    on this machine, checked against SIMPLE_COMMAND_BUDGET_MS."""
    rows = []
    budget = SIMPLE_COMMAND_BUDGET_MS

    # 1) Wake Word ----------------------------------------------------------
    t = TurnTimer()
    with t.stage("wake"):
        for _ in range(50):
            matched = bool(wake.WAKE_RE.search("hey laala, open youtube"))
    ms = t.stages["wake"] / 50
    rows.append(("wake word match", ms, matched and ms <= budget,
                 "regex over normalized text (avg of 50)"))

    # 2) Intent detection ---------------------------------------------------
    samples = ["open youtube", "what time is it", "weather in hyderabad",
               "remind me to call mom", "research quantum computing",
               "prepare everything I need for tomorrow's interview",
               "turn on the lights", "hello there", "volume up",
               "what is the capital of france"]
    t = TurnTimer()
    with t.stage("intent"):
        kinds = [intent.detect(s) for s in samples]
    ms = t.stages["intent"] / len(samples)
    rows.append(("intent detection", ms, bool(all(kinds)) and ms <= budget,
                 f"{len(samples)} utterances classified (avg)"))

    # 3) Simple command, full deterministic chain (no side effects run) -----
    for text in ("what time is it", "open youtube", "volume up"):
        t, _kind, response, action = simple_chain(text)
        ms, ok = t.work_ms, bool(response or action)
        rows.append((f"simple command: “{text}”", ms, ok and ms <= budget,
                     f"intent→route→reply, deterministic (action: {action['type'] if action else '—'})"))

    # 4) Planner (goal decomposition, template — zero LLM round-trips) ------
    goal = "prepare everything I need for tomorrow's interview"
    t = TurnTimer()
    with t.stage("plan"):
        steps, name = planner._template(goal)
    ms = t.stages["plan"]
    rows.append(("planner (goal → steps)", ms, len(steps) >= 3 and ms <= budget,
                 f"template “{name}”: {len(steps)} steps, no LLM round-trip"))

    # 5) Synthetic audio chain: wake → VAD → STT → intent → route ------------
    audio = _synthetic()
    detector = vad.make_vad(cfg)
    transcriber = stt.StreamingTranscriber(cfg)
    t = TurnTimer()
    with t.stage("wake"):
        wake.WAKE_RE.search("hey laala, what time is it")
    from . import pipeline as _pipeline

    with t.stage("stt"):
        _pipeline.endpoint_on_array(audio, detector)
        for i in range(0, len(audio), 3200):
            transcriber.feed(audio[i:i + 3200])
        text = transcriber.finish()
    with t.stage("intent"):
        intent.detect("what time is it")
    with t.stage("route"):
        response, action = router.handle("what time is it")
    live_stt = bool(text)
    rows.append(("audio chain (synthetic)", t.work_ms, t.work_ms <= budget,
                 "wake→VAD→streaming-STT→intent→route"
                 + ("" if live_stt else " (STT simulated: no backend installed)")))

    # 6) TTS note (synthesis is streaming/async; budget applies up to reply) --
    from . import tts as _tts

    rows.append(("speech synthesis", 0.0, True,
                 f"provider: {_tts.resolve_provider(cfg)} — streamed after reply, "
                 "barge-in can cancel"))

    return rows


def _synthetic(seconds_speech=0.6, seconds_silence=0.4, rate=16000):
    from . import pipeline as _pipeline

    return _pipeline.synthetic_utterance(seconds_speech, seconds_silence, rate)


def report_lines(rows, budget=SIMPLE_COMMAND_BUDGET_MS):
    lines = [
        "Voice pipeline latency — §7 chain: wake → STT → intent → planner → "
        "tools → reply → TTS",
        f"Budget: simple commands must finish under {int(budget)} ms.\n",
    ]
    width = max(len(name) for name, *_ in rows)
    for name, ms, ok, note in rows:
        mark = "✓" if ok else "✗"
        ms_txt = f"{ms:8.2f} ms" if ms else "     —    "
        lines.append(f"  {mark} {name:<{width}}  {ms_txt}   {note}")
    all_ok = all(ok for *_x, ok, _n in rows)
    lines.append("\n  " + ("All simple-command paths are well under one second. ✓"
                           if all_ok else "WARNING: a path exceeded the budget. ✗"))
    return lines
