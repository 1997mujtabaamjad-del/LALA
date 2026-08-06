#!/bin/bash
# LALA — macOS one-line installer.
#   curl -fsSL https://raw.githubusercontent.com/1997mujtabaamjad-del/LALA/v1.2/scripts/install-mac.sh | bash
set -e
TAG="v1.2"
REPO="1997mujtabaamjad-del/LALA"
DIR="$HOME/LALA"

echo "==============================================="
echo "  LALA one-click install (macOS)"
echo "==============================================="

PY="$(command -v python3.14 || command -v python3 || true)"
if [ -z "$PY" ]; then
  echo "✖ python3 not found."
  echo "  Fix: run  xcode-select --install   (or: brew install python)"
  echo "  then re-run this one-liner."
  exit 1
fi

if [ ! -d "$DIR" ]; then
  echo "-> downloading $TAG …"
  TMP="$(mktemp -d)"
  curl -fsSL "https://github.com/$REPO/archive/refs/tags/$TAG.zip" -o "$TMP/lala.zip"
  unzip -oq "$TMP/lala.zip" -d "$TMP"
  mv "$TMP/LALA-"* "$DIR"
  rm -rf "$TMP"
fi
cd "$DIR"

echo "-> creating .venv + deps …"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r assistant/requirements.txt

echo "-> installing launcher (~/bin/lala) …"
mkdir -p "$HOME/bin"
cat > "$HOME/bin/lala" <<EOF
#!/bin/bash
cd "$DIR"
exec "$DIR/.venv/bin/python" -m assistant "\$@"
EOF
chmod +x "$HOME/bin/lala"
grep -q 'HOME/bin' "$HOME/.zshrc" 2>/dev/null || echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.zshrc"

if [ -t 0 ]; then
  read -r -p "Start at login? (y/N) " a
  if [ "$a" = "y" ]; then
    .venv/bin/python -m assistant --autostart on
  fi
fi

echo "==============================================="
echo "  ✔ installed — open a NEW Terminal, then:"
echo "      lala --milestone"
echo "      lala"
echo "==============================================="
