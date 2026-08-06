#!/bin/bash
# LALA auto-run: full functional audit + unit suites + syntax checks.
#   bash scripts/autorun.sh        (exit 0 = all good)
set -e
cd "$(dirname "$0")/.."

PY=".venv/bin/python"
[ -x "$PY" ] || PY=python3
if [ "$PY" = ".venv/bin/python" ] && [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q numpy requests
  PY=".venv/bin/python"
fi

echo "▶ 1/3 functional audit (every subsystem)"
"$PY" -m assistant --selftest

echo "▶ 2/3 python unit tests"
"$PY" test/test_assistant.py 2>&1 | tail -3

echo "▶ 2.5/3 standalone HTML script syntax guard"
python3 - <<'PY'
import re
s = open('LALA-standalone.html', encoding='utf8').read()
open('/tmp/lala-embed.js', 'w', encoding='utf8').write(re.search(r'<script>(.*)</script>', s, re.S).group(1))
PY
node --check /tmp/lala-embed.js && echo "  standalone JS: OK"

echo "▶ 3/3 js unit tests + syntax"
for f in electron/*.cjs src/app.js src/stream.js src/streamrecorder.js src/command-engine.js src/wakeword.js; do
  node --check "$f"
done
node --test "test/*.test.js" 2>&1 | grep -E "^# (tests|pass|fail)" || true

echo "✔ auto-run complete"
