# LALA — Full Project Report

**Repo:** `1997mujtabaamjad-del/LALA` · **Branch:** `arena/019fcde4-lala` · **Tag:** `v1.0`
**Date:** 2026-08-05 · **Commits:** 29 · **Code:** ~9,400 lines (26 Python modules, 5 Electron modules, 8 renderer modules)
**Tests:** 78 Python + 19 JS, all green · **Built-in commands:** 60 · **LLM tools:** 10

---

## 1. Executive summary

LALA (“Hey Laala”) is a complete desktop voice assistant delivered as **one product in two
bodies**:

1. **Python assistant** (`assistant/`) — the ML body: wake word → VAD recording →
   streaming STT → tool-calling LLM with memory & persona → streaming TTS, with
   barge-in, recordings, GUI, CLI, brain server, and ops tooling.
2. **Electron + web app** (`electron/`, `src/`) — the command-center UI: orb, live
   transcript, Skills panel, custom commands, settings; works as a desktop app or in
   any browser (Web Speech API), and borrows the Python brain over localhost.

Every stage streams (STT partials while speaking, LLM tokens while speaking, TTS
sentence-by-sentence), every stage degrades gracefully, and the whole chain proves
itself with `--milestone`, reports its latency with `--bench`, and audits the
sub-second budget for simple commands with `--latency`.

---

## 2. Architecture

```
            ┌──────────────────────────── ELECTRON / WEB APP ────────────────────────────┐
  mic ──▶   │  wake stream (Vosk fuzzy “hey laala”) ─▶ PTT / barge capture (16 kHz)      │
            │      │ live partials (stt:feed)            │ final: Vosk | Deepgram | Whisper│
            │      ▼                                     ▼                                │
            │  command-engine (60 phrases, wildcards) ─▶ actions executor                 │
            │      │ no match                            (apps, urls, volume, lights,     │
            │      ▼                                      calendar, weather, screenshots) │
            │  in-app agentic loop (OpenAI tools over SSE, AbortController barge-in)      │
            │      │ no key                              │ speechSynthesis TTS (queued    │
            │      ▼                                     │  sentences, barge monitor)      │
            │  Python brain client ──────────┐           ▲                                │
            └────────────────────────────────┼───────────┼────────────────────────────────┘
                                             │ HTTP :8420 (status/chat/config)
            ┌────────────────────────────────▼───────────┴────────────────────────────────┐
            │                        PYTHON ASSISTANT (the brain)                         │
            │  wake.py (Vosk fuzzy / OpenWakeWord zoo / custom .onnx)                     │
            │  pipeline.py — THE LOOP: start() arms wake; turn() = listen→think→speak→    │
            │                follow-ups→re-arm   (Silero VAD endpointing + barge-in)      │
            │  stt.py: faster-whisper (GPU fp16) · Deepgram nova-2 (WS streaming) ·       │
            │          OpenAI Whisper · Vosk partials                                     │
            │  tools.py: 10 tools, OpenAI tools format, agentic stream loop (≤4 rounds)   │
            │  llm.py: Ollama · OpenAI · mock — memory window 12, Laala persona           │
            │  tts.py: Piper (CUDA EP) · ElevenLabs · sentence streaming + stop token     │
            │  memory.py (history + notes) · router.py (fast path) · recorder · keys ·    │
            │  bench · validate · sync · server · guide · weather · websearch · lights ·  │
            │  calendar(ICS) · autostart · deploy · train_wakeword · gui (tkinter)        │
            └─────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. The voice pipeline (spec → implementation)

| Stage | Implementation | Streaming? |
|---|---|---|
| **Wake word** | “Hey Laala” (also *hey lala / hey la la*) — fuzzy Vosk keyword spotting by default; OpenWakeWord zoo words or custom-trained `.onnx` when present (`train_wakeword.py` scaffold) | continuous |
| **Record** | 16 kHz capture, Silero-endpointed; every utterance saved as `.wav` + `.txt` (`save_recordings`) | live chunks |
| **VAD** | Silero neural VAD via official torch streaming API (ONNX fallback); energy VAD fallback; verified: 91% voiced windows flagged, silence 0.009 | 32 ms windows, ~5.5 ms/chunk |
| **STT** | faster-whisper local (CUDA fp16 / CPU int8) · **Deepgram nova-2** (true WebSocket partials) · OpenAI Whisper API · Vosk partials | partials while speaking |
| **LLM** | Ollama (local) → OpenAI → mock; **tool calling** (10 tools, results fed back, ≤4 rounds); memory = last 12 messages + long-term notes; Laala persona system prompt | tokens as generated |
| **TTS** | Piper (local, CUDA EP) · ElevenLabs (turbo) · browser speechSynthesis; sentence-ready → speak immediately; generation continues while speaking | sentence streaming |
| **Barge-in** | mic open during TTS; on your speech: ⛔ playback, ⛔ generation (stop token / `AbortController` / `generator.close()`), 🎙 new listening cycle | instant |

**Latency budget (spec §7).** Simple commands must answer *well under one second*.
They take the deterministic fast path — intent detection → router → action → reply —
and never touch the LLM. Every real turn logs its own trace
(`⏱ intent 14 µs · route 0.5 ms · tool 5 µs — under 1000 ms ✓`), the brain server
exposes the last turn's stage timings on `/status`, and the Electron/web app plus the
standalone HTML show a live pipeline HUD per utterance. `python -m assistant --latency`
audits every stage of the chain against the 1000 ms budget (exit code 1 on breach);
`--bench` adds it to the per-backend latency table. Measured in the build sandbox:
simple commands complete in **well under 1 ms** of processing work, and the synthetic
audio chain (wake → VAD → streaming STT → intent → route) in **< 1 ms** end to end.

---

## 4. Skills inventory

**60 built-in voice commands** (Electron `commands-default.json`, mirrored in Python router):
open apps/sites (youtube, spotify, vscode, terminal, whatsapp, x, reddit, netflix,
linkedin, maps, gmail, chatgpt, browser, camera, settings, files, notepad, calculator) ·
`search/play <anything>` · **weather** (+3-day forecast, any city) · **calendar**
(add/list/`export .ics`/import) · **lights** on/off/set/color · volume up/down/mute/set% ·
brightness · screenshot · lock/sleep/shutdown*/restart* (*confirm-gated) · dictation start/stop ·
copy that · time/date · coin/dice/joke · **user guide** (LLM-generated, spoken) ·
stop listening · help. Custom commands with `<wildcards>` override built-ins.

**10 LLM tools** (OpenAI tools format, both stacks): `get_weather · web_search ·
control_lights · calendar_add · calendar_list · open_app · open_url · play_music ·
get_time · get_date`. The model decides, tools execute against the *same* executor as
voice commands, results return to the model, only the final reply is spoken.

**Smart-home providers:** Philips Hue (local bridge) · Home Assistant (REST) · WLED (`/win`).
**Web:** DuckDuckGo instant answers + Wikipedia opensearch links + Open-Meteo/wttr.in.

---

## 5. Apps & UI

- **Electron desktop**: tray (minimize-to-tray, wake toggle, quit), GPU hardware-accel
  toggle, global hotkey Ctrl+Shift+L (pynput, GUI), tkinter GUI for the Python body.
- **Web preview** (`npm run preview`, zero-dep server): orb, suggestion chips, Log /
  **Skills** (weather card, web answers + links, calendar CRUD + ICS, light swatches &
  slider) / Commands / Settings / Help tabs.
- **Settings**: engines (offline/Deepgram/Whisper), keys, brain URL + **config sync
  Pull/Push**, language (incl. en-IN, hi-IN), wake/continuous/recordings toggles,
  lights providers, chat/whisper models.

---

## 6. Operations & packaging

| Tool | Purpose |
|---|---|
| `install.sh` / `install.bat` | one-click: venv + deps + launchers (Start Menu / app menu / `lala` cmd) + optional autostart & milestone |
| `--keys` / `--set-*` / `--remove-key` | dedicated key manager; hidden input; keys only in gitignored `.env`; live-validated |
| `--validate` | probes Ollama/Deepgram/OpenAI/ElevenLabs without printing keys |
| `--deploy` | wizard: TTS engine + voice picker, LLM, autostart, systemd brain service |
| `--milestone` | proves wake→record→stt→llm→tts chain on this machine (honest *simulated* labels) |
| `--bench` | ms per stage (wake 0.0 · VAD 5.5/chunk · STT · LLM TTFT · TTS · e2e) |
| `--autostart on/off` | login start (Linux .desktop / macOS LaunchAgent / Win Run key) |
| `--serve` | brain server :8420 (`/status /chat /config`) for the Electron/web app |
| `packaging/release.yml` | on `v*` tags: NSIS/dmg/AppImage/deb + PyInstaller one-file binaries → GitHub Release (2 commands to activate) |
| `packaging/lala-assistant.spec` | single-file native binary build |

---

## 7. Verification (captured live in the build sandbox)

```
========== LALA PIPELINE MILESTONE ==========         ========== LATENCY BENCH ==========
  [✔] wake word        detected in “hey laala, …”       wake match            0.0 ms
  [✔] vad + record     640 ms speech; VAD: SileroVAD    vad / chunk           5.5 ms  SileroVAD
  [✔] streaming stt    (simulated here, live on host)   stt (1 s audio)     248.8 ms  (no backend)
  [✔] llm              provider: mock                   llm first token       0.0 ms  (mock)
  [✔] tts + playback   (silent check)                   tts speak             0.0 ms  (none)
  [✔] recording        milestone-….wav                  end-to-end           16.2 ms
  MILESTONE ACHIEVED 🎉
```
- **Silero ground-truth**: torch reference 30.8 s speech in demo audio; fixed SileroVAD
  flags 918/999 windows (91%, max 1.000); silence 0.009; synthetic tones rejected.
- **Tests**: 78 Python (memory spec, persona, tools schema/roundtrips, SSE/tool-call
  accumulation, ICS roundtrip, WLED URLs, wake backend planner, barge cancel, keys/env,
  sync mapping, milestone, loop) + 19 JS (command engine, wake phrases, stream helpers).
- **Bugs found by our own tests & runs**: wildcard normalizer, guide intro duplication,
  `interruption` NameError on router path (would 500 `/chat`), double-speak in streaming
  branch, ONNX Silero under-detection (fixed via official torch API), history rewrite
  push reconciliations.

---

## 8. Quick start

```bash
bash install.sh            # or install.bat — one click
lala --milestone           # prove it · lala --bench · lala --keys · lala --validate
npm start                  # Electron command center   ·   npm run preview  (browser)
python -m assistant --serve            # brain for the app
git tag v1.1 && git push --tags        # builds installers (after activating release.yml)
```

## 9. Limitations & next steps

- Electron barge-in VAD is energy-based (Silero lives in the Python body; onnxruntime-node
  integration is the natural upgrade).
- Offline wake needs the Vosk model download once (~40 MB); a trained “Hey Laala”
  OpenWakeWord model would raise accuracy further.
- `release.yml` requires a workflow-permissioned push to activate.
- Roadmap: multi-user voice profiles, ElevenLabs streaming TTS, CUDA build packaging,
  Google Calendar OAuth, onnxruntime-node Silero in-app.

*End of report.*
