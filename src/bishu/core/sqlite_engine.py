"""SQLite database memory engine for persistent long-term conversation & telemetry storage."""

import os
import sqlite3
import time
from pathlib import Path


class SQLiteEngine:
    """SQLite Relational Database Manager for Laalaa AI Assistant."""

    def __init__(self, db_path: Path = None):
        if db_path is None:
            db_path = Path.home() / ".bishu" / "laalaa.db"
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(str(self.db_path), check_same_thread=False)

    def _init_db(self):
        """Initialize SQLite database tables for chat history, system events, and user facts."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 1. Chat Conversation History Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS chat_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        sender TEXT,
                        message TEXT,
                        language TEXT
                    )
                """)

                # 2. System Resource Telemetry Events Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT,
                        cpu_percent REAL,
                        ram_percent REAL,
                        message TEXT
                    )
                """)

                # 3. User Preferences & Key-Value Facts Table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_facts (
                        key_name TEXT PRIMARY KEY,
                        val_value TEXT,
                        updated_at TEXT
                    )
                """)

                conn.commit()
                print(f"[SQLiteEngine] SQLite Database initialized at: {self.db_path}")
        except Exception as e:
            print(f"[SQLiteEngine] Database init error: {e}")

    def log_chat(self, sender: str, message: str, language: str = "auto"):
        """Save a chat message entry to SQLite database."""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO chat_history (timestamp, sender, message, language) VALUES (?, ?, ?, ?)",
                    (ts, sender, message, language)
                )
                conn.commit()
        except Exception as e:
            print(f"[SQLiteEngine] Log chat error: {e}")

    def log_system_event(self, cpu: float, ram: float, message: str):
        """Save system resource telemetry event to SQLite database."""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO system_events (timestamp, cpu_percent, ram_percent, message) VALUES (?, ?, ?, ?)",
                    (ts, cpu, ram, message)
                )
                conn.commit()
        except Exception as e:
            print(f"[SQLiteEngine] Log system event error: {e}")

    def set_fact(self, key: str, value: str):
        """Store or update a user fact or setting in SQLite database."""
        try:
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO user_facts (key_name, val_value, updated_at) VALUES (?, ?, ?)",
                    (key, str(value), ts)
                )
                conn.commit()
        except Exception as e:
            print(f"[SQLiteEngine] Set fact error: {e}")

    def get_fact(self, key: str, default=None) -> str:
        """Retrieve a user fact or setting from SQLite database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT val_value FROM user_facts WHERE key_name = ?", (key,))
                row = cursor.fetchone()
                if row:
                    return row[0]
        except Exception as e:
            print(f"[SQLiteEngine] Get fact error: {e}")
        return default

    def get_recent_chats(self, limit: int = 10) -> list:
        """Fetch recent conversation entries from SQLite database."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT timestamp, sender, message FROM chat_history ORDER BY id DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                return list(reversed(rows))
        except Exception as e:
            print(f"[SQLiteEngine] Get recent chats error: {e}")
        return []
