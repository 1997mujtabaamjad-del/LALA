"""
Entry point.

  python -m assistant            # GUI (needs a display)
  python -m assistant --chat     # terminal voice-less REPL (text in, text out)
  python -m assistant --setup    # download the Piper voice + warm checks
  python -m assistant --serve    # local brain server for the Electron/web app
  python -m assistant --deploy   # guided ElevenLabs/Piper + service deployment
  python -m assistant --autostart on|off
  python -m assistant --milestone [--speak]   # prove the full pipeline works
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
    from . import vad as vadmod
    print(f"  VAD:               ",
          "Silero (neural)" if (cfg.get("prefer_silero", True) and vadmod.available())
          else "energy threshold (pip install silero-vad onnxruntime for neural)")
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
    parser.add_argument("--validate", action="store_true",
                        help="test configured API keys (Ollama/Deepgram/OpenAI/ElevenLabs)")
    parser.add_argument("--keys", action="store_true",
                        help="interactive API-key manager (separate from --deploy)")
    parser.add_argument("--set-deepgram", metavar="KEY",
                        help="save Deepgram key to assistant/.env (visible in shell "
                             "history — prefer --keys)")
    parser.add_argument("--set-openai", metavar="KEY", help="save OpenAI key")
    parser.add_argument("--set-elevenlabs", metavar="KEY", help="save ElevenLabs key")
    parser.add_argument("--remove-key", choices=["deepgram", "openai", "elevenlabs"],
                        help="remove a key from assistant/.env")
    parser.add_argument("--milestone", action="store_true",
                        help="run the full pipeline self-check (wake→record→stt→llm→tts)")
    parser.add_argument("--speak", action="store_true",
                        help="with --milestone: play the TTS stage aloud")
    args = parser.parse_args()

    if args.setup:
        setup()
        return
    if args.validate:
        from .validate import main as validate_main
        validate_main()
        return
    if args.keys or args.remove_key or args.set_deepgram or args.set_openai \
            or args.set_elevenlabs:
        from . import keys

        updates = {}
        if args.set_deepgram:
            updates["deepgram"] = args.set_deepgram
        if args.set_openai:
            updates["openai"] = args.set_openai
        if args.set_elevenlabs:
            updates["elevenlabs"] = args.set_elevenlabs
        if updates or args.remove_key:
            if args.remove_key:
                keys.write_env(remove=[args.remove_key])
                print(f"  {args.remove_key}: removed from assistant/.env")
            for short, value in updates.items():
                ok = keys.set_and_check(short, value)
                print(f"  {short}: {'✔ valid' if ok else '✖ rejected'} "
                      "(saved to assistant/.env)")
        else:
            keys.interactive()
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
    if args.milestone:
        from . import config, pipeline

        print("\n========== LALA PIPELINE MILESTONE ==========")
        ok_all = True
        for stage, ok, note in pipeline.run_milestone(config.load(), speak=args.speak):
            ok_all = ok_all and ok
            print(f"  [{'✔' if ok else '✖'}] {stage:16} {note}")
        print("=" * 46)
        print("  MILESTONE ACHIEVED 🎉 full chain operational:"
              if ok_all else "  MILESTONE INCOMPLETE — see ✖ stages above")
        print("  wake → record(+VAD) → streaming STT → LLM → TTS(+barge-in)\n")
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
