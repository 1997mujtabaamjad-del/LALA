"""Mobile Gateway Engine providing Telegram Bot integration for controlling Laalaa from your phone."""

import os
import json
import time
import urllib.request
import urllib.parse
import threading
from bishu.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID


class MobileGatewayEngine:
    """Connects Laalaa AI to your smartphone via Telegram Bot for remote voice/text control & alert notifications."""

    def __init__(self, telegram_token: str = TELEGRAM_BOT_TOKEN, app_callback=None):
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN", telegram_token)
        self.app_callback = app_callback
        self.is_running = False
        self.active_chat_id = os.getenv("TELEGRAM_CHAT_ID", TELEGRAM_CHAT_ID)

    def start_telegram_bot(self, token: str = None):
        """Start background Telegram Bot long-polling listener."""
        if token:
            self.telegram_token = token
        if not self.telegram_token:
            print("[MobileGatewayEngine] Telegram Bot Token not set. Set TELEGRAM_BOT_TOKEN in config.py or environment to talk to Laalaa from your phone.")
            return

        print(f"[MobileGatewayEngine] Starting Telegram Mobile Assistant Bot (Token: {self.telegram_token[:6]}...)...")

        def _bot_poll():
            offset = 0
            self.is_running = True
            while self.is_running:
                try:
                    url = f"https://api.telegram.org/bot{self.telegram_token}/getUpdates?offset={offset}&timeout=10"
                    req = urllib.request.Request(url, headers={"User-Agent": "LaalaaAssistant/1.0"})
                    with urllib.request.urlopen(req, timeout=12) as resp:
                        data = json.loads(resp.read().decode("utf-8"))
                        for result in data.get("result", []):
                            offset = result.get("update_id", offset) + 1
                            msg = result.get("message", {})
                            chat_id = msg.get("chat", {}).get("id")
                            text = msg.get("text", "")

                            if chat_id:
                                self.active_chat_id = chat_id

                            if text and chat_id:
                                print(f"[MobileGatewayEngine] Received message from Telegram phone: '{text}'")
                                reply = self._handle_telegram_command(text)
                                self.send_telegram_msg(reply, chat_id=chat_id)

                except Exception as err:
                    time.sleep(2)

        threading.Thread(target=_bot_poll, daemon=True).start()

    def _handle_telegram_command(self, text: str) -> str:
        """Process incoming Telegram bot commands from smartphone."""
        cmd = text.strip()

        # Handle Telegram slash commands
        if cmd == "/start":
            return "Walaikum Assalam! Main Laalaa hoon — beauty with brains. Aapka Telegram mobile assistant active hai. Type any command or question!"

        elif cmd == "/help":
            return (
                "📱 Laalaa Telegram Commands:\n"
                "- Type any question or command (e.g. 'how are you', 'weather in Delhi')\n"
                "- 'open youtube' / 'open notepad'\n"
                "- 'light on' / 'light off'\n"
                "- 'camera scan' / 'yolo'\n"
                "- '/status' for system CPU/RAM metrics"
            )

        elif cmd == "/status":
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                return f"📊 Laalaa System Telemetry:\nCPU: {cpu:.1f}%\nRAM: {ram:.1f}%\nStatus: Online & Ready!"
            except Exception:
                return "Laalaa System Status: Online & Active!"

        # Pass through to Laalaa LangGraph app callback
        if self.app_callback:
            try:
                reply = self.app_callback(cmd)
                if reply:
                    return reply
            except Exception as e:
                return f"Laalaa execution info: {e}"

        return "Command received on Laalaa!"

    def send_telegram_msg(self, text: str, chat_id: int = None):
        """Send message or notification back to phone via Telegram."""
        target_chat = chat_id or self.active_chat_id
        if not self.telegram_token or not target_chat:
            return

        def _send_worker():
            try:
                url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
                payload = json.dumps({"chat_id": target_chat, "text": text}).encode("utf-8")
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json", "User-Agent": "LaalaaAssistant/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    pass
            except Exception as e:
                print(f"[MobileGatewayEngine] Send Telegram msg info: {e}")

        threading.Thread(target=_send_worker, daemon=True).start()
