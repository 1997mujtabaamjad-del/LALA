"""FastAPI Mobile Gateway for Flutter & React Native Mobile Apps."""

import json
import threading

try:
    from fastapi import FastAPI
    import uvicorn
    HAS_FASTAPI = True
except Exception:
    FastAPI = None
    uvicorn = None
    HAS_FASTAPI = False


class MobileAPIServer:
    """FastAPI & WebSocket REST Server for Flutter / React Native Mobile Apps."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8000, command_callback = None):
        self.host = host
        self.port = port
        self.command_callback = command_callback
        self.app = None
        if HAS_FASTAPI and FastAPI:
            self._init_api()

    def _init_api(self):
        self.app = FastAPI(title="Laalaa Mobile API")

        @self.app.get("/")
        def root():
            return {"system": "Laalaa AI Assistant", "status": "online", "webrtc": "ready"}

        @self.app.get("/command")
        def run_command(cmd: str):
            if self.command_callback:
                res = self.command_callback(cmd)
                return {"success": True, "command": cmd, "response": res}
            return {"success": False, "response": "Command handler not connected."}

    def start_server(self):
        """Start FastAPI mobile server in a background daemon thread."""
        if not HAS_FASTAPI or not uvicorn or not self.app:
            print("[MobileAPIServer] FastAPI / uvicorn not installed. Run: pip install fastapi uvicorn")
            return

        print(f"[MobileAPIServer] Mobile REST API Server running at http://{self.host}:{self.port}")

        def _run_server():
            try:
                uvicorn.run(self.app, host=self.host, port=self.port, log_level="warning")
            except Exception as e:
                print(f"[MobileAPIServer] Server error: {e}")

        threading.Thread(target=_run_server, daemon=True).start()
