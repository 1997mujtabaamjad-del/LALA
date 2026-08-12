# Bishu J.A.R.V.I.S. — Advanced Local AI Companion & System Assistant

**Bishu** is an advanced, high-performance local AI companion inspired by J.A.R.V.I.S., featuring real-time voice recognition, OpenAI Whisper offline speech-to-text, Piper Neural TTS, Ultralytics YOLOv8 computer vision, Perplexity real-time web search, PyAutoGUI desktop automation, and an iconic Iron Man Arc Reactor HUD.

---

## 🚀 Quick Start Guide

### 1. Activate Virtual Environment (Git Bash)
```bash
cd /c/Users/mmujt/bishu
source venv/Scripts/activate
```

### 2. Install Project Dependencies
```bash
pip install -r requirements.txt
python -m pip install -e .
```

### 3. Launch Bishu
```bash
python -m bishu
# OR double click run.bat in File Explorer
```

---

## 🎙️ Complete Voice & Text Command Reference

| Command Phrase | Action Executed |
| :--- | :--- |
| **`Bishu`** / **`Laalaa`** | Activates wake-word listener |
| **`How are you?`** / **`How r u`** | Bishu responds warmly in voice as a close friend |
| **`Tell me about yourself`** | Bishu introduces its capabilities |
| **`Open YouTube`** | Opens YouTube in default browser |
| **`Play Believer`** / **`Play <song>`** | Automatically searches and plays requested song/video on YouTube |
| **`Open Visual Studio Code`** | Launches VS Code |
| **`Open Notepad`** / **`Notepad`** | Launches Windows Notepad |
| **`Open Calculator`** / **`Calc`** | Launches Windows Calculator |
| **`Open Chrome`** / **`Open Safari`** | Launches web browser |
| **`Open WhatsApp`** | Opens WhatsApp Web |
| **`Open Folder Downloads`** | Opens Windows Downloads folder |
| **`Open Folder Desktop`** | Opens Windows Desktop folder |
| **`Open Folder Documents`** | Opens Windows Documents folder |
| **`Search Google for <topic>`** | Searches Google for topic |
| **`Search YouTube for <topic>`** | Searches YouTube for video topic |
| **`Weather in <City>`** | Queries Open-Meteo live weather API for city temperature & wind |
| **`Who is <person>`** / **`Search <topic>`** | Perplexity-style live web search via Wikipedia & DuckDuckGo |
| **`What do you see`** / **`YOLO scan`** | Runs YOLOv8 object detection on webcam/screen and speaks findings |
| **`Open camera`** / **`Camera preview`** | Opens live camera video preview with real-time YOLO bounding boxes |
| **`Camera 0`** / **`Camera 1`** / **`Camera 2`** | Switches active camera index (0 = default, 1 = external USB webcam) |
| **`Volume Up`** / **`Volume Down`** / **`Mute`** | Controls Windows system master volume |
| **`Show Desktop`** / **`Minimize All`** | Toggles Windows desktop view |
| **`Screenshot`** | Takes full desktop screenshot & saves to `~/.bishu/screenshots/` |
| **`Clean Temp`** | Safely cleans Windows temporary files |
| **`Stop Bishu`** / **`Close Bishu`** | Shuts down Bishu AI assistant gracefully |

---

## ⚙️ Configuration (`src/bishu/config.py`)

- **`OLLAMA_MODEL`**: Set your preferred local LLM (`qwen2.5:0.5b`, `gemma2:2b`, `deepseek-r1:1.5b`, `llama3.1:latest`).
- **`MINIMAX_API_KEY`**: Optional MiniMax Cloud AI API key.
- **`CAMERA_INDEX`**: Active camera index (`0` = default webcam, `1` = USB camera).
- **`RAM_CRITICAL_LLM_LIMIT`**: RAM safety cap set to `85.0%` to prevent laptop freezes.

---

## 🛠️ Architecture & System Modules
- **`src/bishu/app.py`**: Non-blocking Qt main event loop & thread-safe signal dispatcher.
- **`src/bishu/core/visual_engine.py`**: 60 FPS Iron Man Arc Reactor HUD with glass command bar & draggable canvas.
- **`src/bishu/core/audio_engine.py`**: Deadlock-free single-stream rolling buffer microphone listener.
- **`src/bishu/core/voice_engine.py`**: High-fidelity SAPI5 / PowerShell System.Speech text-to-speech engine.
- **`src/bishu/core/stt_engine.py`**: OpenAI Whisper local offline Speech-To-Text engine.
- **`src/bishu/core/vision_ai.py`**: Ultralytics YOLOv8 computer vision object detection engine.
- **`src/bishu/core/search_engine.py`**: Perplexity-style live web search engine.
- **`src/bishu/core/automation_engine.py`**: PyAutoGUI, PyWhatKit, and Subprocess command executor.
- **`src/bishu/core/ai_engine.py`**: MiniMax AI & Ollama LLM client with auto-model discovery.
