"""Automation engine utilizing PyWhatKit, PyAutoGUI, Subprocess, YOLO Vision AI, Graphify Knowledge Graph, and Smart Home Engine."""

import os
import time
import shutil
import tempfile
import webbrowser
import subprocess
from pathlib import Path

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False

try:
    import pywhatkit
    HAS_PYWHATKIT = True
except Exception:
    pywhatkit = None
    HAS_PYWHATKIT = False


class AutomationEngine:
    """Runs automated system actions, app launchers, folder openers, media controls, YOLO Vision AI, Graphify Knowledge Graph, and Smart Home Controls."""

    def __init__(self):
        self.vision_ai = None
        self.code_agent = None
        self.graph_engine = None
        self.smarthome_engine = None

    def run(self, action: str, task: dict = None) -> tuple:
        """Execute action, returns (success: bool, description: str)."""
        if task is None:
            task = {}

        action = action.lower().strip()
        print(f"[AutomationEngine] Multilingual action: '{action}'")

        # 1. Stop / Close Laalaa
        if any(kw in action for kw in ["stop laalaa", "close laalaa", "exit laalaa", "band karo", "khatam karo", "alvida"]):
            return True, "EXIT_APP"

        # 2. Smart Home IoT Commands
        if any(kw in action for kw in ["light", "pankha", "fan", "ac", "plug", "socket", "ghar ka status", "smart home"]):
            if not self.smarthome_engine:
                from bishu.core.smarthome_engine import SmartHomeEngine
                self.smarthome_engine = SmartHomeEngine()
            sh_success, sh_desc = self.smarthome_engine.process_voice_command(action)
            if sh_success:
                return True, sh_desc

        # 3. Graphify Knowledge Graph Query
        elif any(kw in action for kw in ["graphify", "knowledge graph", "memory graph", "show graph"]):
            if not self.graph_engine:
                from bishu.core.graphify_engine import GraphifyEngine
                self.graph_engine = GraphifyEngine()
            summary = self.graph_engine.get_summary()
            return True, summary

        # 4. Autonomous Self-Correcting Code Generation
        elif action.startswith("code ") or "write code" in action or "make code" in action or "python script" in action:
            spec = action.replace("write code for", "").replace("write code", "").replace("make code for", "").replace("code ", "").strip()
            if not self.code_agent:
                from bishu.core.code_agent import CodeAgent
                self.code_agent = CodeAgent()

            final_code = self.code_agent.self_correcting_loop(spec)
            print("\n✅  ALL TESTS PASS.  Final code ↓\n")
            print(final_code)
            return True, f"Code generated and verified for {spec}. Check terminal for output."

        # 5. Pure Urdu / Hindi Self Introduction
        elif any(kw in action for kw in ["tell me about yourself", "introduce yourself", "who are you", "who r u", "aap kaun hain", "kaun ho tum"]):
            return True, "Main Laalaa hoon, aapka shakhsi AI saathi! Main Graphify knowledge graph, YOLO vision, smart home control, aur web search ke sath aapki khidmat mein hazir hoon."

        # 6. Pure Urdu / Hindi Greetings
        elif any(kw in action for kw in ["aap kaise hain", "kiya haal hai", "aapka kiya haal hai", "kaise ho", "kaise ho aap", "how are you", "how r u"]):
            return True, "Main bilkul khairiyat se hoon, aap bataiye aapka kya haal hai?"
        elif any(kw in action for kw in ["assalamu alaikum", "assalam o alaikum", "aadaab", "namaste", "hello", "hi laalaa", "hey laalaa"]):
            return True, "Walaikum Assalam! Main Laalaa hoon, farmaiye main aapki kya khidmat kar sakta hoon?"

        # 7. Camera Selection Commands
        elif any(kw in action for kw in ["camera 0", "webcam 0"]):
            if not self.vision_ai:
                from bishu.core.vision_ai import VisionAIEngine
                self.vision_ai = VisionAIEngine()
            return True, self.vision_ai.set_camera_index(0)

        elif any(kw in action for kw in ["camera 1", "webcam 1", "external camera"]):
            if not self.vision_ai:
                from bishu.core.vision_ai import VisionAIEngine
                self.vision_ai = VisionAIEngine()
            return True, self.vision_ai.set_camera_index(1)

        elif any(kw in action for kw in ["open camera", "camera preview", "live camera", "camera kholo"]):
            if not self.vision_ai:
                from bishu.core.vision_ai import VisionAIEngine
                self.vision_ai = VisionAIEngine()
            return self.vision_ai.open_live_camera_preview(duration=12)

        # 8. YOLO Vision Objects Scan
        elif any(kw in action for kw in ["yolo", "what do you see", "camera scan", "kya dikh raha hai"]):
            try:
                if not self.vision_ai:
                    from bishu.core.vision_ai import VisionAIEngine
                    self.vision_ai = VisionAIEngine()
                return self.vision_ai.scan_and_detect()
            except Exception as e:
                return False, f"YOLO vision error: {e}"

        # 9. Play Songs on YouTube ("play <song>", "gaana bajao <song>")
        elif action.startswith("play ") or "gaana bajao" in action or "song" in action:
            topic = action.replace("play ", "").replace("gaana bajao", "").replace("song", "").strip()
            if HAS_PYWHATKIT and pywhatkit:
                try:
                    pywhatkit.playonyt(topic)
                    return True, f"YouTube par '{topic}' chala raha hoon."
                except Exception as e:
                    print(f"[AutomationEngine] PyWhatKit info: {e}")
            webbrowser.open(f"https://www.youtube.com/results?search_query={topic}")
            return True, f"YouTube par '{topic}' dhoond raha hoon."

        # 10. Search Google
        elif "search" in action or "khojo" in action or "talash" in action:
            topic = action.replace("search google for", "").replace("search ", "").replace("khojo", "").replace("talash karo", "").strip()
            if HAS_PYWHATKIT and pywhatkit:
                try:
                    pywhatkit.search(topic)
                    return True, f"Google par '{topic}' dhoond raha hoon."
                except Exception:
                    pass
            webbrowser.open(f"https://www.google.com/search?q={topic}")
            return True, f"Google par '{topic}' dhoond raha hoon."

        # 11. Open YouTube / Chrome / WhatsApp / VS Code
        elif "youtube" in action or "you tube" in action:
            webbrowser.open("https://www.youtube.com")
            return True, "YouTube khol raha hoon."
        elif "chrome" in action or "browser" in action:
            webbrowser.open("https://www.google.com")
            return True, "Google Chrome khol raha hoon."
        elif "whatsapp" in action or "whats app" in action:
            webbrowser.open("https://web.whatsapp.com")
            return True, "WhatsApp Web khol raha hoon."
        elif "visual studio code" in action or "vs code" in action or "vscode" in action:
            try:
                if os.name == "nt":
                    os.system("start code")
                else:
                    subprocess.Popen(["code"])
                return True, "Visual Studio Code khol raha hoon."
            except Exception as e:
                return False, f"Failed to open VS Code: {e}"

        # 12. Application Launchers (Notepad, Calculator)
        elif "notepad" in action or "text editor" in action or "notepad kholo" in action:
            try:
                if os.name == "nt" and hasattr(os, "startfile"):
                    os.startfile("notepad.exe")
                else:
                    subprocess.Popen(["notepad.exe"], shell=True)
                return True, "Notepad khol raha hoon."
            except Exception as e:
                return False, f"Failed to open Notepad: {e}"
        elif "calculator" in action or "calc" in action or "calculator kholo" in action:
            try:
                if os.name == "nt" and hasattr(os, "startfile"):
                    os.startfile("calc.exe")
                else:
                    subprocess.Popen(["calc.exe"], shell=True)
                return True, "Calculator khol raha hoon."
            except Exception as e:
                return False, f"Failed to open Calculator: {e}"

        # 13. Volume & Desktop Controls
        elif "volume up" in action or "aawaz badao" in action:
            if HAS_PYAUTOGUI and pyautogui:
                for _ in range(5):
                    pyautogui.press("volumeup")
                return True, "Aawaz bada di hai."
        elif "volume down" in action or "aawaz kam karo" in action:
            if HAS_PYAUTOGUI and pyautogui:
                for _ in range(5):
                    pyautogui.press("volumedown")
                return True, "Aawaz kam kar di hai."
        elif "show desktop" in action or "desktop dikhao" in action:
            if HAS_PYAUTOGUI and pyautogui:
                pyautogui.hotkey("win", "d")
                return True, "Desktop dikha raha hoon."

        # 14. Screenshot
        elif "screenshot" in action or "photo kheencho" in action:
            try:
                if HAS_PYAUTOGUI and pyautogui:
                    screenshot_dir = Path.home() / ".bishu" / "screenshots"
                    screenshot_dir.mkdir(parents=True, exist_ok=True)
                    file_path = screenshot_dir / f"screenshot_{int(time.time())}.png"
                    pyautogui.screenshot(str(file_path))
                    return True, "Screen ki tasveer le li hai."
            except Exception as e:
                return False, f"Failed to capture screenshot: {e}"

        elif action.startswith("open ") or "kholo" in action:
            target = action.replace("open ", "").replace("kholo", "").strip()
            webbrowser.open(target if target.startswith("http") else f"https://www.google.com/search?q={target}")
            return True, f"'{target}' khol raha hoon."

        return False, f"Command '{action}' not recognized."
