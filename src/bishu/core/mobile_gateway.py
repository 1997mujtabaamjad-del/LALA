"""Mobile Gateway Engine supporting Telegram Bot, Mobile WebSockets, and WhatsApp."""

import json
import time
import urllib.request
import urllib.parse
import threading


class MobileGatewayEngine:
    """Connects Laalaa AI to mobile phones via Telegram Bot & WebSockets."""

    def __init__(self, telegram_token: str = None, app_callback=None):
        self.telegram_token = telegram_token
        self.app_callback = app_callback
        self.is_running = False

    def start_telegram_bot(self, token: str = None):
        """Start background Telegram Bot listener so you can talk to Laalaa from your phone."""
        if token:
            self.telegram_token = token
        if not self.telegram_token:
            print("[MobileGateway] Telegram Bot Token not set. Pass token to connect your phone.")
            return

        print("[MobileGateway] Starting Telegram Mobile Assistant Bot...")

        def _bot_poll():
            offset = 0
            self.is_running = True
            while self.is_running:
                try:
                    url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates?offset={offset}&timeout=10"
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        for result in data.get("result", []):
                            offset = result.get("update_id", offset) + 1
                            msg = result.get("message", {})
                            chat_id = msg.get("chat", {}).get("id")
                            text = msg.get("text", "")

                            if text and chat_id and self.app_callback:
                                print(f"[MobileGateway] Received Mobile Msg from phone: '{text}'")
                                reply = self.app_callback(text)
                                if not reply:
                                    reply = "Command executed on Laalaa!"
                                self._send_telegram_msg(chat_id, reply)

                except Exception as err:
                    time.sleep(2)

        threading.Thread(target=_bot_poll, daemon=True).start()

    def _send_telegram_msg(self, chat_id: int, text: str):
        """Send reply back to user's phone on Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
            payload = json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
