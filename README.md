# LALA 🎙️

**LALA** is a voice command assistant for your desktop — now with **two engines**:

## ⬇️ One-click install

**End users** — grab a ready installer from **GitHub Releases** (built automatically
on every `v*` tag by the release pipeline shipped at `packaging/release.yml`;
activate it once with the two commands noted in that file):
- `LALA Setup .exe` (Windows NSIS) · `.dmg` (macOS) · `.AppImage` / `.deb` (Linux)
- `lala-assistant(.exe)` — single-file Python assistant binary (PyInstaller)

**From source** — double-click:
- **Windows:** `install.bat`
- **Linux / macOS:** `install.sh` (or `bash install.sh`)

Both create a venv, install every dependency (STT/TTS/VAD/wake + optional Electron
UI), add a **Start Menu / app-menu / Desktop launcher**, then offer the milestone
self-check and start-at-login. Afterwards:

```bash
lala                # run the assistant   (.venv/bin/python -m assistant)
lala --milestone    # prove the whole pipeline
lala --keys         # add your API keys
```

In the web preview, **▶ Run demo** plays a full scripted conversation (wake →
time → live weather → calendar add → lights → coin → joke → sign-off) with
spoken replies — no mic needed.

Developers: `npm run dist` builds installers locally; `git tag v1.0 && git push --tags`
triggers the release pipeline.

---

1. **`assistant/` — the Python Jarvis-style assistant** (voice conversation, Q&A with a
   real LLM, memory, wake word). See [Python assistant](#-python-assistant-jarvis-mode).
2. **Electron desktop app + web preview** — command/control UI (apps, volume, screenshots,
   dictation, custom commands). See [Electron / web app](#electron--web-app).

---

## 🐍 Python assistant (Jarvis mode)

Implements the full spec:

| Spec | Implementation |
|---|---|
| Python | `assistant/` package |
| OpenAI API **or** local LLM (Ollama) | `assistant/llm.py` — auto-detects Ollama at `localhost:11434`, falls back to OpenAI, then to an offline demo mode |
| Whisper (STT) | `assistant/stt.py` — local `faster-whisper`, **Deepgram nova-2** (with true WebSocket streaming partials), or the OpenAI Whisper API |
| ElevenLabs **or** Piper (TTS) | `assistant/tts.py` — local Piper (free, private) or ElevenLabs |
| Wake word via OpenWakeWord | `assistant/wake.py` — **“Hey Laala”** default: any phrase fuzzy-spotted offline via Vosk; zoo words / custom .onnx use OpenWakeWord when installed |
| Voice conversation | continuous conversation: keeps listening for follow-ups until you go quiet or say “stop listening” |
| Answer questions | LLM with concise spoken answers |
| Remember previous conversation | `assistant/memory.py` — history + long-term notes persisted to disk |
| Open apps | `assistant/router.py` — apps, websites, search, weather, volume, power |

### Run it

```bash
cd assistant
pip install -r requirements.txt     # every part is optional — degrades gracefully
python -m assistant --setup         # check components + download the Piper voice
python -m assistant                 # desktop GUI (tkinter)
python -m assistant --chat          # terminal REPL (no mic needed — great first test)
python -m assistant --serve         # local brain server for the Electron/web app
```

### ☁️ ElevenLabs deployment

```bash
export ELEVENLABS_API_KEY=…        # or paste it in the wizard
python -m assistant --deploy
```

The guided wizard validates your key, lists **your ElevenLabs voices**, lets you pick
one (lowest-latency `eleven_turbo_v2_5` by default), then optionally installs
**start-at-login** and (on Linux) a **systemd user service** for the brain server.

### Streaming speech

The brain streams tokens (Ollama/OpenAI) and Piper/ElevenLabs starts speaking the
**first sentence while the model is still writing the rest** — much lower latency.

### One brain, two bodies

With `--serve` running, the **Electron/web LALA app** (below) gets the Python brain for
free: any phrase that isn't a hard command is sent to `http://127.0.0.1:8420/chat` and
answered by Ollama/OpenAI with the same conversation memory. Configure it in the app's
Settings → *Python brain*. The bridge is CORS-open on localhost only.

Skills in action:

```
you> open youtube            → opens the browser
you> remember that I like masala chai
you> what do you remember?   → "I remember: I like masala chai."
you> why is the sky blue?    → answered by Ollama/OpenAI, spoken by Piper/ElevenLabs
```

Say **“Hey Laala”** (or click 🎤 Talk) and the orb beeps, listens until silence,
transcribes with Whisper, answers, and *keeps listening* for natural follow-ups —
say “stop listening” to hand her back to the wake word.
Shut-down/restart always asks for confirmation.

Everything degrades gracefully: no mic → text chat; no Ollama → OpenAI; no keys →
offline demo mode. The Electron app in this repo remains the richer *command center* UI.

### ⚡ Everything streams (fast feel)

1. **STT streams**: partial transcript types along *while you speak* (Deepgram
   WebSocket / Vosk / live partials in the app).
2. **LLM streams**: tokens arrive as generated (Ollama & OpenAI SSE), including the
   final answer of **tool-calling rounds** — tool execution stays silent.
3. **Sentence-ready → TTS**: the moment a sentence closes it's sent to Piper /
   ElevenLabs / speechSynthesis and spoken immediately.
4. **Generation continues while speaking**: the TTS worker consumes the token
   stream concurrently; barge-in still cancels instantly.

Perceived latency ≈ first spoken sentence, not full answer.

### 🧰 Tool calling (actions)

The LLM doesn't just chat — it **uses your skills as tools**:

1. Every skill is a function schema (`assistant/tools.py`, OpenAI tools format):
   `get_weather · web_search · control_lights · calendar_add · calendar_list ·
   open_app · open_url · play_music · get_time · get_date`
2. `chat_with_tools()` advertises them to Ollama/OpenAI with every request
3. When the model emits `tool_calls`: each tool runs, its result is fed back as a
   `tool` message, and the loop continues (max 4 rounds)
4. Only the **final reply is spoken**

The Electron/web app has the same loop in-app (Settings → OpenAI key): the model
calls tools that map onto the existing action executor, and each call shows as a
🔧 line in the Log. Unmatched phrases fall back to the Python brain, then to a
polite miss. The deterministic router stays as the zero-latency fast path for
exact commands.

### 🔄 Config sync (one brain, two bodies)

The brain server exposes `GET/PUT /config`; the app's Settings → *Python brain*
has **⬇ Pull /  Push** buttons. Keys (OpenAI/Deepgram/ElevenLabs), name,
language, recordings/continuous flags and all smart-light settings map 1:1
(`assistant/sync.py`, pure + tested) — configure once, works in both apps.

### ⏱️ Latency bench

```bash
python -m assistant --bench
```
```
  wake match                      0.0 ms   regex over normalized text
  vad / chunk                     0.4 ms   SileroVAD
  stt (1 s audio)                12.1 ms   live / simulated
  llm first token               240.0 ms   ollama
  tts speak                     180.0 ms   piper
  end-to-end (synthetic)         31.0 ms   vad+stt+llm+tts
```

### 🏁 The milestone: one unified pipeline

```bash
python -m assistant --milestone          # add --speak to hear the TTS stage
```
```
========== LALA PIPELINE MILESTONE ==========
  [✔] wake word        detected in “hey laala, open youtube”
  [✔] vad + record     600 ms speech segmented; runtime VAD: SileroVAD
  [✔] streaming stt    simulated transcript (install faster-whisper/deepgram/vosk for live)
  [✔] llm              provider: ollama
  [✔] tts + playback   provider: piper (silent check; use --speak to hear it)
  [✔] recording        milestone-1733….wav
==============================================
  MILESTONE ACHIEVED 🎉 full chain operational:
  wake → record(+VAD) → streaming STT → LLM → TTS(+barge-in)
```

Every stage runs on real backends when installed and is honestly labeled
*simulated* otherwise. The **whole loop lives inside the pipeline**
(`assistant/pipeline.py`): `Pipeline.start()` arms the wake word, each wake
runs `turn()` — VAD-endpointed recording with live partials → best STT final →
plugged-in thinking (router/LLM/memory) → streaming TTS you can barge into →
utterance saved → follow-up listening until silence or “stop listening”.
The orchestrator only supplies `think` and the end-of-conversation flag.

### Power features

- **Barge-in (interruption)**, full spec in both stacks: while TTS plays, the mic
  stays open (Silero/Energy VAD). The instant you start speaking:
  1. playback stops immediately,
  2. the in-flight **LLM generation is cancelled** (stop token in Python streams /
     `AbortController` on the app's SSE fetch),
  3. a **new listening cycle** starts and your interruption becomes the next turn.
  In the app this works both when the wake stream is armed *and* via a dedicated
  barge monitor during any spoken reply (auto-endpointed capture → transcript).
- **Silero VAD**: endpointing and barge-in use the **Silero neural VAD** via the
  official `silero-vad` streaming API (torch JIT per 32 ms chunk; ONNX fallback),
  verified against real speech (91% of voiced windows flagged, silence rejected);
  energy threshold remains the zero-dependency fallback. `--setup` shows which is
  active; disable with `prefer_silero: false`.
- **Streaming STT**: partial transcript appears *while you speak* — Python streams
  mic chunks through a live Vosk recognizer (GUI status shows the words forming,
  final answer still comes from Whisper when installed); Electron push-to-talk feeds
  the same streaming recognizer so the interim bubble types along, with Whisper API
  as the cloud final.
- **Recording**: every command's audio is saved as a timestamped `.wav` + `.txt`
  transcript — Python: `assistant/data/recordings/`, Electron: the OS *Recordings*
  folder. Toggle in Settings (`save_recordings`).
- **Barge-in**: start talking while LALA speaks and she shuts up and listens.
  Python: a mic monitor watches RMS during playback (grace period + sustained
  threshold beat speaker bleed) and cancels the audio, then transcribes your
  interruption. Electron/web: the wake stream flips into command capture the
  moment you talk over her voice; Space/orb also cancel TTS instantly.
- **GPU acceleration**: Whisper STT auto-uses CUDA with **float16** when ctranslate2
  sees a GPU (else CPU/int8); Piper uses onnxruntime's **CUDAExecutionProvider** when
  present; Ollama manages its own GPU. `--setup` prints what it found, and the GUI +
  Electron settings have GPU/hardware-acceleration toggles. No GPU? Everything just
  works on CPU.
- **Global hotkey** in the GUI: `Ctrl+Shift+L` = push-to-talk (`pip install pynput`).
- **Start at login**: `python -m assistant --autostart on|off` (Linux / macOS / Windows).
- **Native executable**: `pip install pyinstaller && pyinstaller packaging/lala-assistant.spec`.
- **Custom “Hey LALA” wake model**: `python -m assistant.train_wakeword --record 50`
  records your positives, `--train` prints the exact upstream OpenWakeWord steps.

---

## Electron / web app

It runs in **two modes from the same codebase**:

| Mode | How to run | Speech recognition | What it can do |
|---|---|---|---|
| **Desktop app** (Electron) | `npm start` | **Offline** (Vosk) and/or **Cloud** (OpenAI Whisper API) | Full system control |
| **Web app / preview** | `npm run preview` | Built-in **Web Speech API** (Chrome/Edge) | Websites, dictation, info — great for trying it out |

---

## Quick start

```bash
npm install          # installs Electron (Vosk is optional, see below)
npm start            # launch the desktop app
```

Web preview (no Electron needed, works in Chrome/Edge with a microphone):

```bash
npm run preview      # → http://localhost:4173
```

Run the unit tests:

```bash
npm test
```

## How to talk to LALA

- **Wake word:** just say **“Hey LALA”** followed by your command (e.g. *“Hey LALA, open YouTube”*).
  Runs 100% locally on the offline Vosk engine — needs `npm install vosk` + the model download.
  In the browser preview, say it (or type/click it) too; it's stripped before matching.
- **Desktop push-to-talk:** hold **Space** and speak, then release. Or click the orb —
  click once to start, click again to send.
- **Web:** click the orb to toggle continuous listening, then just speak.
- Tip: click any example chip in the UI to simulate a command.
- **Runs in the background:** closing the window minimizes LALA to the system tray.
  The tray menu shows it, toggles the wake word, and quits for real.

## Speech engines

### 1. Offline — Vosk (private, no internet)

```bash
npm install vosk     # optional dependency with prebuilt binaries
```

Then in the app: **Settings → Download model (~40 MB)**. This fetches the small English
Vosk model into your user-data folder. Offline recognition is English-only.

Vosk uses N-API, so the prebuilt binary normally loads inside Electron as-is. If you get
a module version error, rebuild it for Electron once:

```bash
npx electron-rebuild -f -w vosk
```

The offline engine also powers the **“Hey LALA” wake word** — LALA listens locally with a
lightweight streaming recognizer, beeps when it hears you, and endpoints on silence.

### 1½. Deepgram — lowest-latency cloud STT

Set `DEEPGRAM_API_KEY` (or paste it in Settings). Batch transcription uses **nova-2**,
and the Python assistant's live partials upgrade from local Vosk to **true WebSocket
streaming** (`wss://api.deepgram.com …interim_results=true`) when the key is present.
In the Electron app, pick *Cloud — Deepgram* under Speech engine.

Keys are read from the environment or a gitignored `assistant/.env`
(see `assistant/.env.example`). Test them all locally without exposing secrets:

```bash
python -m assistant --validate
```

### Key manager (separate from --deploy)

```bash
python -m assistant --keys            # interactive: hidden paste, validate, remove
python -m assistant --set-deepgram KEY --set-openai KEY   # scriptable
python -m assistant --remove-key elevenlabs
```

Keys are written **only** to `assistant/.env` (never `config.json`, never git),
comments in the file are preserved, and each key is live-validated on save.

### 2. Cloud — OpenAI Whisper (any language, best accuracy)

In the app: **Settings → paste your OpenAI API key**, pick a model
(`whisper-1` or `gpt-4o-mini-transcribe`). Your audio is sent directly from LALA to
OpenAI's transcription endpoint — nowhere else.

### 3. Web Speech API (browser mode only)

Free, zero-setup, continuous listening with live interim results. Needs a Chromium
browser and internet. This is what `npm run preview` uses.

The **Auto** engine setting prefers offline when the model is ready, otherwise cloud.

## Built-in commands

Say things like:

- *"open youtube / google / github / gmail / maps / chatgpt / spotify / vs code / whatsapp / twitter / reddit / netflix / linkedin / camera"*
- *"open browser / terminal / notepad / calculator / files / settings"*
- *"search for <anything>"*, *"play <anything>"* (YouTube)
- *"weather"*, *"weather in hyderabad"*, *"calculate 18 percent of 450"*
- *"volume up / down / mute"*, *"set volume to 40 percent"*
- *"brightness up / down"*
- *"take a screenshot"*
- *"minimize / maximize / close window"*, *"quit lala"*
- *"start dictation"* → speak freely → *"stop dictation"* → text is copied to your clipboard
- *"copy that"* — copies your last transcript
- *"what time is it"*, *"what's the date"*
- *"flip a coin"*, *"roll a dice"*, *"tell me a joke"*
- **Weather (spoken + forecast)**: *"weather"*, *"weather in hyderabad"*, *"forecast"* —
  Open-Meteo (no key): current conditions **plus a 3-day outlook**; wttr.in IP fallback.
  The Skills tab shows a clickable weather card.
- **Web answers (spoken + links)**: *"who is ada lovelace"*, *"what is rayleigh scattering"* —
  DuckDuckGo instant answers with a **Wikipedia fallback**; the Skills panel also lists
  clickable result links; falls back to a browser search when nothing's found
- **Calendar (+ ICS interop)**: *"add dentist appointment tomorrow at 3pm"*,
  *"what's on my calendar"*, *"export my calendar"* — persisted locally, spoken summaries,
  **export/import standard .ics** so Google/Outlook/Apple calendars round-trip
  (Skills tab has Export/Import buttons)
- **Smart lights**: *"lights on/off"*, *"set lights to 40 percent"*, *"lights to warm/blue"* —
  **Philips Hue, Home Assistant, or WLED** (Settings → Smart lights), plus on/off,
  brightness and color-swatch controls in the Skills tab
- *"lock computer"*, *"sleep computer"*
- *"shut down computer"*, *"restart computer"* — **LALA always asks you to confirm first**
- *"help"* — shows everything it understands
- *"user guide"* — LALA **generates a speaking tutorial with the LLM** (wake word,
  push-to-talk, follow-ups, barge-in, example commands) and **reads it aloud**;
  offline, a built-in guide is spoken instead. Interrupt anytime by talking.

## Custom commands

Open the **Commands** tab and map any phrase to an action:

- **Open URL** — `open notion` → `https://www.notion.so`
- **Launch app** — `open spotify` → `spotify` (a program on your PATH)
- **Run shell command** — power users only; runs through your shell
- **Say something** — LALA replies with your text
- **Copy text to clipboard**

Wildcards work in custom commands too: phrase `meet with <who>` + value
`https://meet.google.com/new?authuser={who}` — `<name>` in the phrase becomes `{name}`
in the value. Custom commands take priority over built-ins.

Settings and custom commands are stored in Electron's `userData` directory
(e.g. `%APPDATA%/lala` on Windows, `~/Library/Application Support/lala` on macOS,
`~/.config/lala` on Linux); the web preview uses `localStorage`.

## Project structure

```
electron/
  main.cjs            app window + IPC
  preload.cjs         context bridge (window.lala)
  asr.cjs             Vosk (offline) + Whisper API (cloud) engines
  actions.cjs         desktop action executor (apps, volume, power, …)
  store.cjs           settings / custom-command persistence
src/
  index.html          UI (shared by desktop + web)
  app.js              app logic, command dispatch
  command-engine.js   phrase matching (pure functions, unit-tested)
  commands-default.json  built-in vocabulary
  recorder.js         mic capture → webm (cloud) + 16 kHz PCM (offline)
  web-speech.js       Web Speech API adapter (browser mode)
scripts/
  preview-server.mjs  zero-dependency static server for web mode
test/
  command-engine.test.js
```

## Packaging installers

`package.json` already contains a full `electron-builder` config (icon included).
Installers land in `release/`:

```bash
npm run dist          # current platform
npm run dist:win      # Windows NSIS installer (.exe)
npm run dist:mac      # macOS .dmg
npm run dist:linux    # AppImage + .deb
```

On Linux, building the `.deb` needs `dpkg`; building Windows installers works from
Windows (or Linux with Wine). Building macOS `.dmg`s requires macOS.

## Notes & troubleshooting

- **Linux volume** uses `pactl` or `amixer`; brightness uses `brightnessctl`/`xbacklight`.
- **Windows volume** simulates the hardware media keys via PowerShell — it works with any
  audio endpoint the OS routes to.
- If the microphone doesn't work in the desktop app, check your OS microphone privacy
  settings (Windows: Settings → Privacy → Microphone).
- The web preview needs a secure context (localhost or HTTPS) and a Chromium browser.
