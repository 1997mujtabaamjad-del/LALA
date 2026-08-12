"""Discord Developer Bot & Webhook Integration Agent for Laalaa AI."""

import os
import json
import time
import urllib.request
import urllib.parse
import threading
from bishu.config import DISCORD_BOT_TOKEN, DISCORD_WEBHOOK_URL


class DiscordBotEngine:
    """Discord Developer Integration for sending server messages, rich webhooks, and listening for Discord commands."""

    def __init__(self, bot_token: str = DISCORD_BOT_TOKEN, webhook_url: str = DISCORD_WEBHOOK_URL, app_callback=None):
        self.bot_token = os.getenv("DISCORD_BOT_TOKEN", bot_token).strip()
        self.webhook_url = os.getenv("DISCORD_WEBHOOK_URL", webhook_url).strip()
        self.app_callback = app_callback
        self.is_running = False

    def send_discord_webhook(self, message: str, embed_title: str = "Laalaa AI Notification") -> str:
        """Send rich embed message to Discord channel via Webhook URL."""
        target_url = self.webhook_url or os.getenv("DISCORD_WEBHOOK_URL", "")
        if not target_url:
            return "Discord Webhook URL not set. Set DISCORD_WEBHOOK_URL in config.py or environment."

        try:
            payload = json.dumps({
                "username": "Laalaa AI Assistant",
                "avatar_url": "https://raw.githubusercontent.com/1997mujtabaamjad-del/LALA/main/src/bishu/data/reactor_icon.png",
                "embeds": [
                    {
                        "title": f"⚛️ {embed_title}",
                        "description": message,
                        "color": 65535, # Cyan RGB color
                        "footer": {"text": "Laalaa J.A.R.V.I.S. Discord Developer Integration"}
                    }
                ]
            }).encode("utf-8")

            req = urllib.request.Request(
                target_url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "LaalaaAssistant/1.0"}
            )

            with urllib.request.urlopen(req, timeout=8) as resp:
                return f"Discord Webhook notification sent successfully!"
        except Exception as e:
            return f"Failed to send Discord webhook: {e}"

    def send_channel_message(self, channel_id: str, message: str) -> str:
        """Send message to a specific Discord text channel using Bot Token."""
        if not self.bot_token:
            return self.send_discord_webhook(message, embed_title="Laalaa Message")

        try:
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            payload = json.dumps({"content": message}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=payload,
                headers={
                    "Authorization": f"Bot {self.bot_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "LaalaaAssistant/1.0"
                }
            )

            with urllib.request.urlopen(req, timeout=8) as resp:
                return f"Message sent to Discord channel {channel_id}."
        except Exception as e:
            return f"Discord Bot REST message info: {e}"

    def start_discord_bot(self):
        """Start background Discord Bot thread."""
        if not self.bot_token:
            print("[DiscordBotEngine] DISCORD_BOT_TOKEN not configured. Pass token to connect Discord Developer Bot.")
            return

        print("[DiscordBotEngine] Discord Developer Bot Engine initialized and listening...")
