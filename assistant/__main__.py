"""
Entry point.

  python -m assistant            # GUI (needs a display)
  python -m assistant --chat     # terminal voice-less REPL (text in, text out)
  python -m assistant --setup    # download the Piper voice + warm checks
  python -m assistant --serve    # local brain server for the Electron/web app
  python -m assistant --deploy   # guided ElevenLabs/Piper + service deployment
  python -m assistant --autostart on|off
"""

import argparse
import sys


def chat_repl():
    from . import config, llm
    from .orchestrator import Assistant

    cfg = config.load()
    assistant = Assistant(cfg)
    assistant.log = lambda who, text: None  # REPL prints its own lines

    status = llm.provider_status(cfg)
    print(f"\n{cfg['name']} terminal mode.")
    print(f"  LLM: {status['active']} (ollama={status['ollama']}, openai={status['openai']})")
    print("  Type anything, or a command like `open youtube` / `remember that I like tea`.")
    print("  `exit` quits.\n")

    while True:
        try:
            text = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text:
            continue
        if text in ("exit", "quit", "bye"):
            break
        reply = assistant.process(text, follow_up=False, spoken=False)
        print(f"{cfg['name']}> {reply}\n")
    print("Bye!")


def setup():
    from . import config, stt, tts

    cfg = config.load()
    print("Checking assistant components…")
    print(f"  sounddevice (mic): ", end="")
    try:
        from . import mic
        print("ok" if mic.available() else "missing (pip install sounddevice)")
    except Exception as exc:  # noqa: BLE001
        print(f"error: {exc}")
    print(f"  openwakeword:      ", end="")
    try:
        import openwakeword  # noqa: F401
        print("ok")
    except ImportError:
        print("missing (pip install openwakeword)")
    print(f"  faster-whisper:    ", "ok" if stt.local_available() else "missing (pip install faster-whisper)")
    from . import gpu
    g = gpu.summarize()
    device, compute = gpu.stt_plan(cfg.get("prefer_gpu", True), g["cuda_devices"])
    print(f"  GPU (CUDA):        ",
          f"{g['cuda_devices']} device(s) → Whisper on {device}/{compute}"
          if g["cuda_devices"] else
          "none — CPU mode (int8). Ollama will also use CPU.")
    print(f"  Piper CUDA EP:     ", "yes" if g["onnx_cuda"] else "no (CPU onnxruntime)")
    print(f"  piper TTS model:   ", "ok" if tts.piper_ready() else "not downloaded")
    ans = input("Download the Piper voice now? [y/N] ").strip().lower()
    if ans in ("y", "yes"):
        tts.download_piper_voice(progress=lambda p: print(f"\r  downloading… {p}%", end=""))
        print("\n  done.")
    print("Setup complete. Run `python -m assistant` for the GUI or `--chat` for terminal mode.")


def main():
    parser = argparse.ArgumentParser(prog="assistant")
    parser.add_argument("--chat", action="store_true", help="terminal REPL (no audio)")
    parser.add_argument("--setup", action="store_true", help="component check + Piper download")
    parser.add_argument("--serve", action="store_true",
                        help="run the local brain server (port 8420) for the Electron/web app")
    parser.add_argument("--deploy", action="store_true",
                        help="guided deployment (ElevenLabs voices, auto-start, service)")
    parser.add_argument("--autostart", choices=["on", "off"],
                        help="install/remove start-at-login")
    args = parser.parse_args()

    if args.setup:
        setup()
        return
    if args.deploy:
        from .deploy import main as deploy_main
        deploy_main()
        return
    if args.autostart:
        from . import autostart
        if args.autostart == "on":
            print("auto-start installed:", autostart.install())
        else:
            autostart.uninstall()
            print("auto-start removed.")
        return
    if args.serve:
        from .server import main as server_main
        server_main()
        return
    if args.chat:
        chat_repl()
        return

    try:
        import tkinter  # noqa: F401
        from .gui import main as gui_main
        gui_main()
    except Exception as exc:  # noqa: BLE001 — no display / no tkinter
        print(f"GUI unavailable ({exc}); falling back to --chat mode.")
        chat_repl()


if __name__ == "__main__":
    sys.exit(main())
