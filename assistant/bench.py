"""
Latency report: milliseconds per pipeline stage on THIS machine.

  python -m assistant --bench

Stages: wake match · VAD per-chunk · streaming-STT final · LLM first token ·
TTS first audio · synthetic end-to-end. Live backends are measured when
installed/reachable, otherwise honestly reported as simulated (0 ms).
"""

import time

import numpy as np

from . import llm, pipeline, stt, tts, vad, wake


def _ms(fn, *a, **kw):
    t0 = time.perf_counter()
    out = fn(*a, **kw)
    return (time.perf_counter() - t0) * 1000, out


def run_bench(cfg):
    rows = []

    # wake word matching
    ms, ok = _ms(lambda: bool(wake.WAKE_RE.search("hey laala, open youtube")))
    rows.append(("wake match", ms, "regex over normalized text"))

    # VAD per chunk
    detector = vad.make_vad(cfg)
    tone = (0.3 * np.sin(np.arange(1280) * 0.2) * 32767).astype(np.int16)
    t0 = time.perf_counter()
    for _ in range(20):
        detector.speech(tone)
    rows.append(("vad / chunk", (time.perf_counter() - t0) * 1000 / 20,
                 detector.__class__.__name__))

    # streaming STT over 1 s synthetic audio
    audio = pipeline.synthetic_utterance(0.6, 0.4)
    transcriber = stt.StreamingTranscriber(cfg)
    ms, text = _ms(lambda: _feed_finish(transcriber, audio))
    rows.append(("stt (1 s audio)", ms,
                 "live" if text else "no backend (simulated 0-work)"))

    # LLM time-to-first-token
    provider = llm.resolve_provider(cfg)
    if provider in ("ollama", "openai"):
        gen = llm.ask_stream(cfg, None, "Say hello")
        t0 = time.perf_counter()
        next(gen, None)
        ttft = (time.perf_counter() - t0) * 1000
        gen.close()
        rows.append(("llm first token", ttft, provider))
    else:
        rows.append(("llm first token", 0.0, f"{provider} (simulated)"))

    # TTS first audio
    tprov = tts.resolve_provider(cfg)
    if tprov != "none":
        ms, _ = _ms(tts.speak, "Bench.", cfg)
        rows.append(("tts speak", ms, tprov))
    else:
        rows.append(("tts speak", 0.0, "none (simulated)"))

    # synthetic end-to-end (vad sweep + stt + mock llm + silent tts)
    def e2e():
        pipeline.endpoint_on_array(audio, detector)
        tr = stt.StreamingTranscriber(cfg)
        _feed_finish(tr, audio)
        llm.ask(cfg, None, "hello")
        tts.speak("ok", cfg)
    ms, _ = _ms(e2e)
    rows.append(("end-to-end (synthetic)", ms, "vad+stt+llm+tts"))

    # §7 budget: deterministic simple-command chain (intent → route → reply)
    from . import latency as _lat

    timer, _kind, reply, _action = _lat.simple_chain("what time is it")
    budget = _lat.SIMPLE_COMMAND_BUDGET_MS
    rows.append(("simple command e2e", timer.work_ms,
                 f"deterministic path — {reply!r} — "
                 + ("PASS" if reply and timer.work_ms <= budget else "FAIL")
                 + f" (budget {int(budget)} ms)"))

    return rows


def _feed_finish(transcriber, audio):
    for i in range(0, len(audio), 3200):
        transcriber.feed(audio[i:i + 3200])
    return transcriber.finish()
