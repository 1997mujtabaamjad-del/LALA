"""
Dedicated API-key management — separate from the --deploy wizard.

  python -m assistant --keys                     interactive (hidden input)
  python -m assistant --set-deepgram KEY …       scriptable (visible in shell
                                                 history — prefer interactive)
  python -m assistant --remove-key deepgram

Keys are stored ONLY in assistant/.env (gitignored).
"""

import getpass
import os

from . import config, validate

ENV_PATH = os.path.join(config.HERE, ".env")
NAMES = {
    "deepgram": "DEEPGRAM_API_KEY",
    "openai": "OPENAI_API_KEY",
    "elevenlabs": "ELEVENLABS_API_KEY",
}


def read_env(path=ENV_PATH):
    try:
        with open(path, "r", encoding="utf8") as fh:
            return config.parse_env(fh.read())
    except OSError:
        return {}


def write_env(updates=None, remove=None, path=ENV_PATH):
    """Upsert/remove KEY=value lines, preserving comments and other lines."""
    updates = updates or {}
    remove_full = {NAMES[r] for r in (remove or [])}
    try:
        with open(path, "r", encoding="utf8") as fh:
            lines = fh.read().splitlines()
    except OSError:
        lines = []
    seen = set()
    out = []
    for line in lines:
        stripped = line.strip()
        key = stripped.split("=", 1)[0].strip() if "=" in stripped else None
        if key and (key in updates or key in remove_full):
            if key in updates:
                out.append(f"{key}={updates[key]}")
                seen.add(key)
            continue  # replaced or removed
        out.append(line)
    for k, v in updates.items():
        if k not in seen:
            out.append(f"{k}={v}")
    with open(path, "w", encoding="utf8") as fh:
        fh.write("\n".join(out).rstrip() + "\n")
    return path


def mask(key):
    if not key:
        return "—"
    return key[:4] + "…" + key[-2:] if len(key) > 10 else "****"


def status_rows():
    cfg = config.load()
    env = read_env()
    rows = []
    for short, full in NAMES.items():
        value = (env.get(full) or os.environ.get(full)
                 or cfg.get(f"{short}_api_key") or "")
        source = ("env file" if env.get(full)
                  else "environment" if os.environ.get(full)
                  else "config" if cfg.get(f"{short}_api_key") else "not set")
        rows.append((short, source, mask(value)))
    return rows


def _check(short, cfg):
    return {"deepgram": validate.check_deepgram,
            "openai": validate.check_openai,
            "elevenlabs": validate.check_elevenlabs}[short](cfg)


def set_and_check(short, value):
    write_env({NAMES[short]: value})
    cfg = config.load()
    cfg[f"{short}_api_key"] = value
    ok = _check(short, cfg)
    return ok


def interactive():
    print("\n=== LALA key manager === (stored only in assistant/.env)\n")
    while True:
        for short, source, masked in status_rows():
            print(f"  {short:11} {source:12} {masked}")
        print("\n  [d]eepgram  [o]penai  [e]levenlabs  [v]alidate  "
              "[r]emove  [q]uit")
        try:
            choice = input("> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if choice in ("q", "quit", "exit", ""):
            break
        if choice in ("d", "o", "e"):
            short = {"d": "deepgram", "o": "openai", "e": "elevenlabs"}[choice]
            value = getpass.getpass(f"Paste {short} key (hidden): ").strip()
            if not value:
                print("  (empty — skipped)")
                continue
            ok = set_and_check(short, value)
            print("  ✔ valid — saved to assistant/.env" if ok
                  else "  ✖ saved, but the provider rejected it")
        elif choice == "v":
            cfg = config.load()
            for short, _s, _m in status_rows():
                result = _check(short, cfg)
                print(f"  {short:11} {'✔ valid' if result else '✖ / not set'}")
        elif choice == "r":
            which = input("remove which (deepgram/openai/elevenlabs)? ").strip().lower()
            if which in NAMES:
                write_env(remove=[which])
                print(f"  removed {which} from .env")
    print("bye.")
