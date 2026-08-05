# LALA 🎙️

**LALA** is a voice command assistant for your desktop — now with **two engines**:

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
| Whisper (STT) | `assistant/stt.py` — local `faster-whisper`, or the OpenAI Whisper API |
| ElevenLabs **or** Piper (TTS) | `assistant/tts.py` — local Piper (free, private) or ElevenLabs |
| Wake word via OpenWakeWord | `assistant/wake.py` — **“Hey Jarvis”** default (also alexa / hey_mycroft / okay_nabu / tim) |
| Voice conversation | continuous loop with silence endpointing + follow-up window |
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

Say **“Hey Jarvis”** (or click 🎤 Talk) and the orb beeps, listens until silence,
transcribes with Whisper, answers, and stays open a moment for a natural follow-up.
Shut-down/restart always asks for confirmation.

Everything degrades gracefully: no mic → text chat; no Ollama → OpenAI; no keys →
offline demo mode. The Electron app in this repo remains the richer *command center* UI.

### Power features

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
- *"lock computer"*, *"sleep computer"*
- *"shut down computer"*, *"restart computer"* — **LALA always asks you to confirm first**
- *"help"* — shows everything it understands

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
