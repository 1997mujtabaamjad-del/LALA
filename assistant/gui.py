"""
Tkinter desktop GUI: orb status, conversation log, chat box, push-to-talk,
settings (providers + API keys), wake-word status.
"""

import queue
import threading
import tkinter as tk
from tkinter import messagebox, scrolledtext

from . import config, tts
from .orchestrator import Assistant

COLORS = {
    "idle": "#22d3ee",
    "listening": "#a78bfa",
    "thinking": "#fbbf24",
}


class Gui:
    def __init__(self):
        self.cfg = config.load()
        self.ui_queue = queue.Queue()
        self.root = tk.Tk()
        self.root.title(f"{self.cfg['name']} — Voice Assistant")
        self.root.geometry("860x640")
        self.root.configure(bg="#0b1020")

        self._build_ui()
        self.assistant = Assistant(
            self.cfg,
            log=self._log_cb,
            status=self._status_cb,
            confirm=self._gui_confirm,
        )
        self.root.after(100, self._pump_ui)
        self.root.protocol("WM_DELETE_WINDOW", self._quit)
        threading.Thread(target=self.assistant.start, daemon=True).start()
        self._install_hotkey()

    def _install_hotkey(self):
        """Optional global hotkey Ctrl+Shift+L = push-to-talk (needs pynput)."""
        try:
            from pynput import keyboard
        except ImportError:
            return

        def _fire():
            self.root.after(0, self.assistant.push_to_talk)

        listener = keyboard.GlobalHotKeys({"<ctrl>+<shift>+l": _fire})
        listener.daemon = True
        listener.start()
        self._hotkey = listener
        self._log_cb("system", "Global hotkey armed: Ctrl+Shift+L to talk.")

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        bg = "#0b1020"
        panel = "#111833"
        fg = "#e8ecf7"

        top = tk.Frame(self.root, bg=bg)
        top.pack(fill="x", padx=14, pady=10)

        self.orb = tk.Canvas(top, width=84, height=84, bg=bg, highlightthickness=0)
        self.orb.pack(side="left")
        self.orb_circle = self.orb.create_oval(10, 10, 74, 74, fill=COLORS["idle"], outline="")
        self.orb.bind("<Button-1>", lambda e: self.assistant.push_to_talk())

        title = tk.Frame(top, bg=bg)
        title.pack(side="left", padx=12)
        tk.Label(title, text=self.cfg["name"], bg=bg, fg=fg,
                 font=("Segoe UI", 20, "bold")).pack(anchor="w")
        self.wake_label = tk.Label(title, text=f"wake: {self.cfg['wake_word'].replace('_', ' ')}",
                                   bg=bg, fg="#93a0bd", font=("Segoe UI", 10))
        self.wake_label.pack(anchor="w")

        right = tk.Frame(top, bg=bg)
        right.pack(side="right")
        self.status_label = tk.Label(right, text="idle", bg=bg, fg="#34d399",
                                     font=("Segoe UI", 11))
        self.status_label.pack(anchor="e")
        tk.Button(right, text="🎤 Talk", command=self.assistant.push_to_talk,
                  bg="#22d3ee", fg="#08101c", bd=0, padx=10, pady=4).pack(pady=4)
        tk.Button(right, text="Settings", command=self._open_settings,
                  bg=panel, fg=fg, bd=0, padx=10, pady=4).pack(pady=2)

        self.log = scrolledtext.ScrolledText(self.root, bg=panel, fg=fg, bd=0,
                                             font=("Consolas", 11), wrap="word")
        self.log.pack(fill="both", expand=True, padx=14, pady=6)
        self.log.tag_config("you", foreground="#22d3ee")
        self.log.tag_config("assistant", foreground="#a78bfa")
        self.log.tag_config("system", foreground="#93a0bd")

        bottom = tk.Frame(self.root, bg=bg)
        bottom.pack(fill="x", padx=14, pady=10)
        self.entry = tk.Entry(bottom, bg=panel, fg=fg, bd=0,
                              font=("Segoe UI", 12), insertbackground=fg)
        self.entry.pack(side="left", fill="x", expand=True, ipady=6)
        self.entry.bind("<Return>", lambda e: self._send_typed())
        tk.Button(bottom, text="Send", command=self._send_typed,
                  bg="#a78bfa", fg="#08101c", bd=0, padx=14, pady=4).pack(side="left", padx=8)

    def run(self):
        self.root.mainloop()

    # ------------------------------------------------------- ui callbacks
    def _log_cb(self, who, text):
        self.ui_queue.put(("log", who, text))

    def _status_cb(self, text):
        self.ui_queue.put(("status", text, ""))

    def _pump_ui(self):
        try:
            while True:
                kind, a, b = self.ui_queue.get_nowait()
                if kind == "log":
                    who = "assistant" if a == self.cfg["name"] else a
                    self.log.insert("end", f"{a}: {b}\n", who)
                    self.log.see("end")
                else:
                    self.status_label.config(text=a)
                    if a in COLORS:
                        self.orb.itemconfig(self.orb_circle, fill=COLORS[a])
        except queue.Empty:
            pass
        self.root.after(100, self._pump_ui)

    def _gui_confirm(self, text):
        event = threading.Event()
        result = {"ok": False}

        def _ask():
            result["ok"] = messagebox.askyesno("Confirm", f'Run “{text}”?')
            event.set()

        self.root.after(0, _ask)
        event.wait(20)
        return result["ok"]

    def _send_typed(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.entry.delete(0, "end")
        threading.Thread(target=self.assistant.process,
                         args=(text,), kwargs={"spoken": True}, daemon=True).start()

    # ----------------------------------------------------------- settings
    def _open_settings(self):
        win = tk.Toplevel(self.root)
        win.title("Settings")
        win.configure(bg="#0b1020")
        win.geometry("480x520")

        fields = {}

        def row(parent, label, key, show=None):
            tk.Label(parent, text=label, bg="#0b1020", fg="#e8ecf7",
                     anchor="w").pack(fill="x", padx=14, pady=(10, 0))
            e = tk.Entry(parent, bg="#111833", fg="#e8ecf7", bd=0, show=show or "")
            e.insert(0, str(self.cfg.get(key, "")))
            e.pack(fill="x", padx=14, pady=2, ipady=4)
            fields[key] = e

        row(win, "Assistant name", "name")
        row(win, "Persona (blank = built-in Laala personality)", "persona")
        row(win, "Wake word (alexa | hey_jarvis | hey_mycroft | okay_nabu | tim)", "wake_word")
        row(win, "LLM provider (auto | ollama | openai | mock)", "llm_provider")
        row(win, "Ollama model", "ollama_model")
        row(win, "OpenAI API key", "openai_api_key", show="*")
        row(win, "OpenAI model", "openai_model")
        row(win, "ElevenLabs API key", "elevenlabs_api_key", show="*")
        row(win, "STT provider (auto | local | deepgram | openai)", "stt_provider")
        row(win, "Deepgram API key", "deepgram_api_key", show="*")
        row(win, "TTS provider (auto | piper | elevenlabs | none)", "tts_provider")
        row(win, "Hue bridge IP (for smart lights)", "hue_ip")
        row(win, "Hue username/key", "hue_key")
        row(win, "Home Assistant URL", "ha_url")
        row(win, "Home Assistant token", "ha_token", show="*")

        gpu_var = tk.BooleanVar(value=bool(self.cfg.get("prefer_gpu", True)))
        tk.Checkbutton(win, text="Use GPU (CUDA) for Whisper/Piper when available",
                       variable=gpu_var, bg="#0b1020", fg="#e8ecf7",
                       selectcolor="#111833", activebackground="#0b1020",
                       activeforeground="#e8ecf7").pack(anchor="w", padx=14, pady=8)

        def save():
            for key, entry in fields.items():
                self.cfg[key] = entry.get().strip()
            self.cfg["prefer_gpu"] = bool(gpu_var.get())
            config.save(self.cfg)
            self.assistant.cfg = self.cfg
            self.wake_label.config(text=f"wake: {self.cfg['wake_word'].replace('_', ' ')}")
            self._log_cb("system", "Settings saved.")
            win.destroy()

        btn = tk.Frame(win, bg="#0b1020")
        btn.pack(fill="x", padx=14, pady=12)
        tk.Button(btn, text="Save", command=save, bg="#22d3ee", fg="#08101c",
                  bd=0, padx=14, pady=4).pack(side="left")
        tk.Button(btn, text="Download Piper voice (~60 MB)",
                  command=lambda: self._download_piper(win),
                  bg="#111833", fg="#e8ecf7", bd=0, padx=10, pady=4).pack(side="left", padx=8)

    def _download_piper(self, win):
        def _work():
            try:
                tts.download_piper_voice()
                self._log_cb("system", "Piper voice downloaded — local TTS ready.")
            except Exception as exc:  # noqa: BLE001
                self._log_cb("system", f"Piper download failed: {exc}")
        threading.Thread(target=_work, daemon=True).start()

    def _quit(self):
        self.assistant.stop()
        self.root.destroy()


def main():
    Gui().run()


if __name__ == "__main__":
    main()
