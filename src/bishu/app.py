"""Laalaa application — single-stream deadlock-free J.A.R.V.I.S. companion with LangGraph & Telegram Mobile Gateway."""

import sys
import time
import threading
from pathlib import Path

from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal

try:
    from PyQt5.QtWidgets import QApplication
except ImportError as err:
    print(f"[LaalaaApp] QtWidgets unavailable ({err}). Using QCoreApplication fallback.")
    from PyQt5.QtCore import QCoreApplication as QApplication

try:
    from plyer import notification
    HAS_PLYER = True
except Exception:
    HAS_PLYER = False

from bishu.data.paths import memory_file, schedule_file
from bishu.core.memory_engine import MemoryEngine
from bishu.core.sqlite_engine import SQLiteEngine
from bishu.core.monitor_engine import MonitorEngine
from bishu.core.scheduler_engine import SchedulerEngine
from bishu.core.ai_engine import AIEngine
from bishu.core.automation_engine import AutomationEngine
from bishu.core.safety_engine import SafetyEngine
from bishu.core.permission_engine import PermissionEngine
from bishu.core.visual_engine import VisualEngine
from bishu.core.tray_engine import TrayEngine, TraySignals
from bishu.core.audio_engine import AudioEngine
from bishu.core.voice_engine import VoiceEngine
from bishu.core.stt_engine import STTEngine
from bishu.core.search_engine import SearchEngine
from bishu.core.langgraph_engine import LangGraphEngine
from bishu.core.mobile_gateway import MobileGatewayEngine
from bishu.config import (
    OLLAMA_MODEL,
    TELEGRAM_BOT_TOKEN,
    SAMPLE_LIMIT,
    MIN_BASELINE_SAMPLES,
    CPU_HARD_LIMIT,
    RAM_HARD_LIMIT,
    RAM_CRITICAL_LLM_LIMIT,
    CPU_SPIKE_DELTA,
    RAM_SPIKE_DELTA,
    MONITOR_INTERVAL_SECONDS,
    ALERT_COOLDOWN_SECONDS,
    ALERT_RED_SECONDS,
    SCHEDULER_INTERVAL_MS,
    AUDIO_THRESHOLD,
)


def notify_desktop(title: str, message: str):
    """Send native desktop notification."""
    if HAS_PLYER:
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Laalaa Assistant",
                timeout=5
            )
        except Exception:
            pass
    print(f"[Laalaa Notification] {title}: {message}")


class AppSignals(QObject):
    """Thread-safe Qt Signals for background workers updating UI."""
    set_thinking = pyqtSignal(bool)
    set_alert = pyqtSignal(bool)


class BishuApp(QObject):
    WAKE_WORDS = ["laalaa", "lala", "hey laalaa", "hey lala", "assalam", "aadaab", "namaste", "bishu", "hey bishu"]

    def __init__(self):
        super().__init__()

        data = Path.home() / ".bishu"
        data.mkdir(parents=True, exist_ok=True)

        self.memory = MemoryEngine(memory_file())
        self.db = SQLiteEngine()
        self.scheduler = SchedulerEngine(schedule_file())
        self.ai = AIEngine(OLLAMA_MODEL)
        self.automation = AutomationEngine()
        self.safety = SafetyEngine()
        self.permissions = PermissionEngine()
        self.monitor = MonitorEngine()
        self.audio = AudioEngine(threshold=AUDIO_THRESHOLD)
        self.voice = VoiceEngine()
        self.stt = STTEngine()
        self.search_engine = SearchEngine()

        # LangGraph Stateful Agent Orchestrator
        self.langgraph = LangGraphEngine(
            ai_engine=self.ai,
            search_engine=self.search_engine,
            automation_engine=self.automation,
            vision_engine=self.automation.vision_ai,
            code_agent=self.automation.code_agent
        )

        # Telegram Mobile Phone Gateway
        self.mobile_gateway = MobileGatewayEngine(
            telegram_token=TELEGRAM_BOT_TOKEN,
            app_callback=self.handle_mobile_command
        )
        if TELEGRAM_BOT_TOKEN:
            self.mobile_gateway.start_telegram_bot()

        cpu_samples = self.memory.get("cpu_samples", [])
        ram_samples = self.memory.get("ram_samples", [])
        self.monitor.cpu_history = cpu_samples[-SAMPLE_LIMIT:]
        self.monitor.ram_history = ram_samples[-SAMPLE_LIMIT:]

        self.last_alert = 0.0
        self.ai_request_running = False
        self.pending_alert_message = ""
        self.last_voice_trigger = 0.0

        # UI — Realistic Arc Reactor HUD with Glass Command Input Bar
        self.orb = VisualEngine()
        if hasattr(self.orb, "setWindowFlags"):
            self.orb.setWindowFlags(
                Qt.FramelessWindowHint
                | Qt.WindowStaysOnTopHint
                | Qt.Tool
            )
        if hasattr(self.orb, "setAttribute"):
            self.orb.setAttribute(Qt.WA_TranslucentBackground, True)
        self.orb.resize(1100, 1100)

        if hasattr(QApplication, "primaryScreen"):
            screen = QApplication.primaryScreen()
            if screen:
                geom = screen.availableGeometry()
                self.orb.move(
                    geom.right() - self.orb.width() - 20,
                    geom.top() + 20,
                )

        # Connect Glass Command Bar signal and Camera Window signal
        if hasattr(self.orb, "command_entered"):
            self.orb.command_entered.connect(self.handle_user_command)
        if hasattr(self.orb, "camera_requested"):
            self.orb.camera_requested.connect(self.open_camera_window)

        # Thread-safe UI Signals
        self.app_signals = AppSignals()
        self.app_signals.set_thinking.connect(self.orb.set_thinking)
        self.app_signals.set_alert.connect(self.orb.set_alert)

        # Timers
        self.anim_timer = QTimer()
        self.anim_timer.timeout.connect(self.tick_anim)
        self.anim_timer.start(33)

        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self.tick_monitor)
        self.monitor_timer.start(MONITOR_INTERVAL_SECONDS * 1000)

        self.scheduler_timer = QTimer()
        self.scheduler_timer.timeout.connect(self.tick_scheduler)
        self.scheduler_timer.start(SCHEDULER_INTERVAL_MS)

        # Tray
        self.signals = TraySignals()
        self.signals.show.connect(self.show_orb)
        self.signals.hide.connect(self.hide_orb)
        self.signals.reload.connect(self.reload_schedule)
        self.signals.exit_app.connect(self.exit_app)

        self.tray = TrayEngine(self.signals)
        self.tray.start()

        # Audio Engine
        self.audio.voice_detected.connect(self.on_voice_detected)
        self.audio.start()

        # Silent Boot: No spoken greeting message on launch (only a quiet desktop notification)
        notify_desktop("Laalaa Online", "Type or speak commands (e.g. 'open youtube', 'notepad', 'how are you').")

    def open_camera_window(self):
        """Open floating camera window with live YOLO vision detection."""
        try:
            from bishu.core.camera_window import CameraWindow
            if not hasattr(self, "cam_win") or self.cam_win is None:
                self.cam_win = CameraWindow()
            self.cam_win.show()
            self.cam_win.raise_()
            self.cam_win.activateWindow()
        except Exception as e:
            print(f"[Laalaa] Error opening camera window: {e}")

    def handle_mobile_command(self, cmd: str) -> str:
        """Handle incoming mobile commands from Telegram phone bot asynchronously."""
        if not cmd:
            return ""
        cmd = cmd.strip()
        print(f"[Laalaa Mobile Gateway] Command from smartphone: '{cmd}'")
        self.db.log_chat(sender="User (Phone)", message=cmd)

        recent_turns = self.db.get_recent_chats(limit=6)
        history = [{"sender": s, "message": m} for _, s, m in recent_turns[:-1]]

        response = self.langgraph.execute(cmd, history=history)
        if response:
            self.db.log_chat(sender="Laalaa", message=response)
            return response
        return "Command executed successfully on Laalaa!"

    def handle_user_command(self, cmd: str):
        """Handle continuous conversation loop commands via LangGraph agent workflow asynchronously."""
        if not cmd:
            return
        cmd = cmd.strip().lower()
        print(f"[Laalaa LangGraph] User Input: '{cmd}'")

        # Log user message into SQLite conversation store
        self.db.log_chat(sender="User", message=cmd)

        self.show_orb()
        self.app_signals.set_thinking.emit(True)

        def _exec_worker():
            try:
                # 1. Fetch recent conversation history from SQLite for LangGraph state
                recent_turns = self.db.get_recent_chats(limit=6)
                history = [{"sender": s, "message": m} for _, s, m in recent_turns[:-1]]

                # 2. Execute stateful LangGraph Agent Workflow
                response = self.langgraph.execute(cmd, history=history)

                if response == "EXIT_APP":
                    exit_msg = "Khuda hafiz! Aap se baat karke bahut accha laga."
                    self.voice.speak(exit_msg)
                    time.sleep(1.5)
                    self.exit_app()
                    return

                if response:
                    print(f"[Laalaa LangGraph Output]: '{response}'")
                    self.db.log_chat(sender="Laalaa", message=response)
                    self.voice.speak(response)
                    notify_desktop("Laalaa", response)
                else:
                    fallback_res = "Main bilkul khairiyat se hoon! Farmaiye main aapki kya khidmat karoon?"
                    self.db.log_chat(sender="Laalaa", message=fallback_res)
                    self.voice.speak(fallback_res)

            except Exception as e:
                print(f"[Laalaa LangGraph] Workflow error: {e}")
                fallback_res = "Main bilkul khairiyat se hoon! Farmaiye main aapki kya khidmat karoon?"
                self.voice.speak(fallback_res)
            finally:
                time.sleep(1)
                self.app_signals.set_thinking.emit(False)

        threading.Thread(target=_exec_worker, daemon=True).start()

    def on_voice_detected(self, volume):
        now = time.monotonic()
        if now - self.last_voice_trigger < 2.5:
            return
        self.last_voice_trigger = now

        print(f"[Laalaa LangGraph] Voice activity detected (level={volume:.3f})")

        def _voice_worker():
            # Allow 1.0 second for the user to complete their spoken sentence
            time.sleep(1.0)
            # Transcribe directly from in-memory audio buffer with dynamic peak gain boosting
            audio_buffer = self.audio.get_buffered_audio()
            spoken_phrase = self.stt.transcribe_buffer(audio_buffer)
            print(f"[Laalaa LangGraph] OpenAI Whisper Transcribed: '{spoken_phrase}'")

            if spoken_phrase:
                self.handle_user_command(spoken_phrase)
            else:
                self.show_orb()
                # Wake-Up Response: Speaks "Ji boss, farmaiye!" out loud
                self.voice.speak("Ji boss, farmaiye!")

        threading.Thread(target=_voice_worker, daemon=True).start()

    def show_orb(self):
        self.orb.show()
        if hasattr(self.orb, "raise_"):
            self.orb.raise_()
        if hasattr(self.orb, "activateWindow"):
            self.orb.activateWindow()

    def hide_orb(self):
        self.orb.hide()

    def reload_schedule(self):
        self.scheduler.reload()

    def exit_app(self):
        try:
            self.audio.stop()
        except Exception:
            pass
        QApplication.instance().quit()

    def tick_anim(self):
        self.orb.rotation = (self.orb.rotation + 0.8) % 360
        self.orb.update()

    def tick_monitor(self):
        def _monitor_worker():
            cpu, ram = self.monitor.sample()

            self.memory.set("cpu_samples", self.monitor.cpu_history)
            self.memory.set("ram_samples", self.monitor.ram_history)

            cpu_hist = self.monitor.cpu_history[:-1]
            ram_hist = self.monitor.ram_history[:-1]

            cpu_base = sum(cpu_hist) / len(cpu_hist) if cpu_hist else cpu
            ram_base = sum(ram_hist) / len(ram_hist) if ram_hist else ram

            enough = (
                len(cpu_hist) >= MIN_BASELINE_SAMPLES
                and len(ram_hist) >= MIN_BASELINE_SAMPLES
            )

            reasons = []

            if cpu >= CPU_HARD_LIMIT:
                reasons.append(f"High CPU: {cpu:.1f}%")
            elif enough and cpu >= cpu_base + CPU_SPIKE_DELTA:
                reasons.append(f"CPU spike: {cpu:.1f}%")

            if ram >= RAM_HARD_LIMIT:
                reasons.append(f"High RAM: {ram:.1f}%")
            elif enough and ram >= ram_base + RAM_SPIKE_DELTA:
                reasons.append(f"RAM spike: {ram:.1f}%")

            if not reasons:
                return

            now = time.monotonic()
            if now - self.last_alert < ALERT_COOLDOWN_SECONDS:
                return

            self.last_alert = now
            message = " | ".join(reasons)

            self.pending_alert_message = message

            events = self.memory.get("system_events", [])
            events.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "cpu": cpu,
                "ram": ram,
                "message": message,
            })
            self.memory.set("system_events", events[-100:])

            self.app_signals.set_alert.emit(True)
            QTimer.singleShot(ALERT_RED_SECONDS * 1000,
                              lambda: self.app_signals.set_alert.emit(False))

            print(f"[Laalaa System Monitor] Resource spike logged: {message}")

            # Send proactive resource spike notification to user's Telegram phone if configured
            if hasattr(self, "mobile_gateway") and self.mobile_gateway:
                self.mobile_gateway.send_telegram_msg(f"⚠️ Laalaa System Alert: {message}")

        threading.Thread(target=_monitor_worker, daemon=True).start()

    def start_ai_suggestion(self, alert_message):
        if self.ai_request_running:
            return

        _, ram = self.monitor.sample()
        if ram >= RAM_CRITICAL_LLM_LIMIT:
            print(f"[Laalaa] RAM is critically high ({ram:.1f}% >= {RAM_CRITICAL_LLM_LIMIT}%). Skipping local LLM inference to protect laptop.")
            return

        self.ai_request_running = True
        self.app_signals.set_thinking.emit(True)

        threading.Thread(
            target=self._ai_worker,
            args=(alert_message,),
            daemon=True,
        ).start()

    def _ai_worker(self, alert_message):
        events = self.memory.get("system_events", [])[-5:]
        prompt = f"""You are Laalaa, a local Windows assistant.

System alert:
{alert_message}

Recent events:
{events}

Give a short practical recommendation.
- Maximum 4 bullet points.
- Prefer reversible actions.
- No registry changes.
- No disabling security.
- No deleting personal files.
- Do not claim you performed an action.
"""

        suggestion = self.ai.generate(prompt)

        self.ai_request_running = False
        self.app_signals.set_thinking.emit(False)

        suggestions = self.memory.get("ai_suggestions", [])
        suggestions.append({
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "alert": alert_message,
            "suggestion": suggestion,
        })
        self.memory.set("ai_suggestions", suggestions[-50:])

        print("\nLAALAA AI SUGGESTION:")
        print(suggestion)

    def tick_scheduler(self):
        self.scheduler.reload()
        due = self.scheduler.due_tasks()

        for task in due:
            action = task.get("action", "")

            if not self.safety.is_allowed(action):
                print(f"Blocked unsafe action: {action}")
                continue

            self.orb.set_task_flash(True)
            QTimer.singleShot(
                4000,
                lambda: self.orb.set_task_flash(False),
            )

            success, description = self.automation.run(action, task)

            actions = self.memory.get("scheduled_actions", [])
            actions.append({
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "action": action,
                "success": success,
                "description": description,
            })
            self.memory.set("scheduled_actions", actions[-100:])


def main() -> int:
    try:
        app = QApplication(sys.argv)
        if hasattr(app, "setQuitOnLastWindowClosed"):
            app.setQuitOnLastWindowClosed(False)

        print("[LaalaaApp] Starting Laalaa AI Assistant GUI...")
        bishu = BishuApp()
        bishu.orb.show()
        print("[LaalaaApp] Laalaa AI Assistant running successfully!")

        return app.exec_()
    except Exception as e:
        print(f"\n[LaalaaApp CRITICAL ERROR]: Failed to start Laalaa GUI: {e}\n")
        import traceback
        traceback.print_exc()
        input("\nPress ENTER to exit...")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
