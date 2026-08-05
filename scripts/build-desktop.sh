#!/usr/bin/env bash
# LALA one-click DESKTOP BUILD (Linux/macOS; from Windows use build-desktop.bat)
#   bash scripts/build-desktop.sh            # build for this OS
#   bash scripts/build-desktop.sh all        # win+mac+linux (needs each OS's toolchain)
#   SKIP_PY=1 bash scripts/build-desktop.sh  # skip the Python one-file binary
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==============================================="
echo "  LALA desktop build"
echo "==============================================="
command -v node >/dev/null 2>&1 || { echo "✖ Node 18+ required"; exit 1; }

if [ ! -x node_modules/.bin/electron-builder ]; then
  echo "→ installing build deps (electron + electron-builder) …"
  npm install --no-audit --no-fund
fi

TARGET="${1:-current}"
case "$TARGET" in
  win)     npx electron-builder --win --publish never ;;
  mac)     npx electron-builder --mac --publish never ;;
  linux)   npx electron-builder --linux --publish never ;;
  all)     npx electron-builder --win --mac --linux --publish never ;;
  current) npx electron-builder --publish never ;;
esac
echo "→ Electron installers in release/"

if [ "${SKIP_PY:-0}" != "1" ] && command -v python3 >/dev/null 2>&1; then
  echo "→ building Python assistant one-file binary …"
  python3 -m pip install --user -q pyinstaller || true
  if python3 -m PyInstaller --version >/dev/null 2>&1; then
    python3 -m PyInstaller packaging/lala-assistant.spec --noconfirm \
      && echo "→ binary in dist/lala-assistant" \
      || echo "  (pyinstaller failed — Electron installer still ready)"
  else
    echo "  (pyinstaller unavailable — skipped)"
  fi
fi

echo "==============================================="
echo "  ✔ done — install from release/ (or dist/)"
echo "==============================================="
