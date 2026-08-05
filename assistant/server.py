"""
Local bridge server: lets the Electron / web LALA app use the Python brain
(LLM answers + conversation memory) for anything that isn't a hard command.

  python -m assistant --serve          # http://127.0.0.1:8420

Endpoints:
  GET  /status   -> {"ok": true, "name": ...}
  POST /chat     {"text": "..."}  ->  {"reply": "..."}   (also stored in memory)
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, config
from .orchestrator import Assistant

DEFAULT_PORT = 8420


def make_server(cfg=None, port=DEFAULT_PORT):
    cfg = cfg or config.load()
    assistant = Assistant(cfg)  # silent by default: log/status are no-ops

    class Handler(BaseHTTPRequestHandler):
        def _json(self, code, payload):
            body = json.dumps(payload).encode("utf8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self):
            if self.path.rstrip("/") == "/status":
                self._json(200, {"ok": True, "name": cfg["name"], "version": __version__})
            elif self.path.rstrip("/") == "/config":
                from . import sync

                self._json(200, {"ok": True, "config": sync.to_electron(config.load())})
            else:
                self._json(404, {"ok": False})

        def do_POST(self):
            if self.path.rstrip("/") == "/config":
                from . import sync

                try:
                    length = int(self.headers.get("Content-Length", 0))
                    payload = json.loads(self.rfile.read(length) or b"{}")
                    patch = sync.to_python(payload)
                    config.save(patch)
                    self._json(200, {"ok": True, "saved": list(patch)})
                except Exception as exc:  # noqa: BLE001
                    self._json(500, {"ok": False, "error": str(exc)})
                return
            if self.path.rstrip("/") != "/chat":
                self._json(404, {"ok": False})
                return
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length) or b"{}")
                text = str(payload.get("text", "")).strip()
                if not text:
                    self._json(400, {"ok": False, "reply": ""})
                    return
                reply = assistant.process(text, follow_up=False, spoken=False)
                self._json(200, {"ok": True, "reply": reply or ""})
            except Exception as exc:  # noqa: BLE001
                self._json(500, {"ok": False, "reply": "", "error": str(exc)})

        def log_message(self, *args):  # keep stdout quiet
            pass

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.assistant = assistant
    return server


def main():
    server = make_server()
    addr = server.server_address
    print(f"LALA brain listening on http://{addr[0]}:{addr[1]} — "
          "the Electron/web app can now ask it anything. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nBye!")
        server.server_close()
