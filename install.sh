#!/usr/bin/env bash
# LALA one-click install (Linux / macOS). Double-click or: bash install.sh
set -euo pipefail
cd "$(dirname "$0")"

echo "=============================================="
echo "  LALA — one-click install"
echo "=============================================="

PY="$(command -v python3.14 || command -v python3 || true)"
if [ -z "$PY" ]; then echo "✖ python3 (3.10–3.14) is required"; exit 1; fi
echo "→ using $PY ($("$PY" --version 2>&1))"
echo "→ python: $PY ($("$PY" --version 2>&1))"

# 1. virtualenv + dependencies -------------------------------------------------
if [ ! -d .venv ]; then
  echo "→ creating .venv …"
  "$PY" -m venv .venv
fi
echo "→ installing Python dependencies (STT/TTS/VAD/wake) …"
.venv/bin/pip install --upgrade pip -q
.venv/bin/pip install -q -r assistant/requirements.txt

# 2. optional Electron UI -------------------------------------------------------
if [ "${SKIP_ELECTRON:-0}" != "1" ] && command -v npm >/dev/null 2>&1; then
  echo "→ installing desktop UI (Electron) …"
  npm install --no-audit --no-fund -q || echo "  (npm failed — Python assistant is still ready)"
else
  echo "→ skipping Electron UI (npm not found or SKIP_ELECTRON=1)"
fi

# 3. launcher + desktop entry ----------------------------------------------------
BIN="$HOME/.local/bin"
mkdir -p "$BIN"
ROOT="$(pwd)"
cat > "$BIN/lala" <<EOF
#!/usr/bin/env bash
cd "$ROOT"
exec "$ROOT/.venv/bin/python" -m assistant "\$@"
EOF
chmod +x "$BIN/lala"
echo "→ launcher: $BIN/lala"

if [ "$(uname)" = "Linux" ]; then
  APPS="$HOME/.local/share/applications"
  mkdir -p "$APPS"
  cat > "$APPS/lala.desktop" <<EOF
[Desktop Entry]
Name=LALA Voice Assistant
Comment=Hey Laala — your desktop voice assistant
Exec=$BIN/lala
Icon=$ROOT/assets/icon.png
Terminal=false
Type=Application
Categories=Utility;
EOF
  echo "→ app menu entry: LALA Voice Assistant"
fi

if [ "$(uname)" = "Darwin" ]; then
  cat > "$HOME/Desktop/LALA.command" <<EOF
#!/bin/bash
"$BIN/lala"
EOF
  chmod +x "$HOME/Desktop/LALA.command"
  echo "→ Desktop/LALA.command created (double-click to run)"
fi

# 4. finish ------------------------------------------------------------------------
echo
echo "=============================================="
echo "  ✔ installed"
echo "     run:        lala            (or .venv/bin/python -m assistant)"
echo "     self-check: lala --milestone"
echo "     keys:       lala --keys"
echo "=============================================="

if [ "${YES:-0}" != "1" ] && [ -t 0 ]; then
  read -r -p "Run the milestone self-check now? [Y/n] " ans
  ans="${ans:-y}"
  if [[ "$ans" =~ ^[Yy] ]]; then .venv/bin/python -m assistant --milestone; fi
  read -r -p "Start at login? [y/N] " ans2
  if [[ "$ans2" =~ ^[Yy] ]]; then .venv/bin/python -m assistant --autostart on; fi
fi
echo "Enjoy — say “Hey Laala” 👋"
