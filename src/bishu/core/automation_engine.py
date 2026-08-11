"""Automation engine utilizing PyWhatKit, PyAutoGUI, Subprocess, YOLO Vision AI, Graphify Knowledge Graph, Smart Home Engine, Voice Engine, Avatar Engine, Vault Engine, Research Engine, Scraper Agent, Image AI Agent, Web Builder, and VSCode Integration."""

import os
import re
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
    """Runs automated system actions, app launchers, YOLO Vision, Smart Home Controls, 2D Avatar, Vault, Research, Scraper, Image AI, Web Builder, and VSCode Integration."""

    def __init__(self):
        self.vision_ai = None
        self.code_agent = None
        self.graph_engine = None
        self.smarthome_engine = None
        self.vault_engine = None
        self.research_engine = None
        self.scraper_agent = None
        self.image_agent = None
        self.web_builder = None
        self.vscode_agent = None

    def run(self, action: str, task: dict = None) -> tuple:
        """Execute action, returns (success: bool, description: str)."""
        if task is None:
            task = {}

        action = action.lower().strip()
        print(f"[AutomationEngine] Multilingual action: '{action}'")

        # 1. Stop / Close Laalaa
        if any(kw in action for kw in ["stop laalaa", "close laalaa", "exit laalaa", "band karo", "khatam karo", "alvida"]):
            return True, "EXIT_APP"

        # 2. AI Image Generator (Stable Diffusion text-to-image with custom aspect ratios)
        elif action.startswith("generate image ") or action.startswith("make photo ") or action.startswith("draw "):
            prompt = action.replace("generate image", "").replace("make photo", "").replace("draw", "").strip()
            aspect = "16:9"
            if " 1:1" in action:
                aspect = "1:1"
            elif " 9:16" in action:
                aspect = "9:16"
            elif " 4:3" in action:
                aspect = "4:3"
            if not self.image_agent:
                from bishu.core.image_agent import ImageAIAgent
                self.image_agent = ImageAIAgent()
            res = self.image_agent.generate_image(prompt, aspect_ratio=aspect)
            return True, res

        # 3. AI Website Template Builder (HTML5 Canvas, CSS Grid, Tailwind JS)
        elif "build website" in action or "build template" in action or "create html website" in action or "make website" in action:
            p_str = action.replace("build website for", "").replace("build website", "").replace("build template for", "").replace("build template", "").replace("create html website for", "").replace("make website for", "").strip()
            if not self.web_builder:
                from bishu.core.web_builder import WebTemplateBuilder
                from bishu.core.ai_engine import AIEngine
                self.web_builder = WebTemplateBuilder(ai_engine=AIEngine())
            res = self.web_builder.build_template(p_str)
            return True, res

        # 4. Web Scraper Agent (Raw URLs, Table Links, Page Paragraphs)
        elif action.startswith("scrape url ") or action.startswith("read url "):
            url = action.replace("scrape url", "").replace("read url", "").strip()
            if not self.scraper_agent:
                from bishu.core.scraper_agent import WebScraperAgent
                self.scraper_agent = WebScraperAgent()
            raw_text = self.scraper_agent.read_raw_url(url)
            return True, f"Raw text extracted from '{url}':\n{raw_text[:500]}..."

        elif "scrape table links" in action or "extract table" in action:
            url = action.replace("scrape table links from", "").replace("scrape table links", "").replace("extract table from", "").strip()
            if not self.scraper_agent:
                from bishu.core.scraper_agent import WebScraperAgent
                self.scraper_agent = WebScraperAgent()
            tables = self.scraper_agent.scrape_table_links(url)
            return True, f"Extracted {len(tables)} table structures from '{url}'."

        elif "extract paragraphs" in action or "scrape paragraphs" in action:
            url = action.replace("extract paragraphs from", "").replace("extract paragraphs", "").replace("scrape paragraphs from", "").strip()
            if not self.scraper_agent:
                from bishu.core.scraper_agent import WebScraperAgent
                self.scraper_agent = WebScraperAgent()
            p_list = self.scraper_agent.extract_paragraphs(url)
            return True, f"Extracted {len(p_list)} text paragraphs from '{url}'."

        # 5. VSCode Workspace Integration (Syntax Validation, Run Tasks, Open Workspace)
        elif "validate syntax" in action or "check syntax" in action:
            f_path = action.replace("validate syntax for", "").replace("validate syntax", "").replace("check syntax for", "").strip()
            if not self.vscode_agent:
                from bishu.core.vscode_agent import VSCodeIntegration
                self.vscode_agent = VSCodeIntegration()
            return True, self.vscode_agent.validate_syntax(f_path)

        elif "vscode task" in action or "run task" in action:
            t_name = action.replace("vscode task", "").replace("run task", "").strip()
            if not self.vscode_agent:
                from bishu.core.vscode_agent import VSCodeIntegration
                self.vscode_agent = VSCodeIntegration()
            return True, self.vscode_agent.run_vscode_task(t_name)

        elif "open workspace" in action or "vscode workspace" in action:
            w_path = action.replace("open workspace", "").replace("vscode workspace", "").strip() or str(Path.cwd())
            if not self.vscode_agent:
                from bishu.core.vscode_agent import VSCodeIntegration
                self.vscode_agent = VSCodeIntegration()
            return True, self.vscode_agent.open_workspace(w_path)

        # 6. AI Code Fixer, Builder & Explainer
        elif "fix clipboard error" in action or "fix clipboard" in action or "fix error" in action:
            if not self.code_agent:
                from bishu.core.code_agent import CodeAgent
                self.code_agent = CodeAgent()
            res = self.code_agent.fix_clipboard_error()
            return True, f"Clipboard Error Auto-Fixed:\n\n```python\n{res}\n```"

        elif "explain code" in action or "explain logic" in action:
            c_snippet = action.replace("explain code", "").replace("explain logic", "").strip()
            if not self.code_agent:
                from bishu.core.code_agent import CodeAgent
                self.code_agent = CodeAgent()
            res = self.code_agent.explain_code(c_snippet)
            return True, res

        # 7. Deep Research Report Generator (College Reports, Business Plans, Slide Deck PPTs)
        elif "college report" in action or "academic report" in action or "research report" in action:
            topic = action.replace("college report on", "").replace("college report", "").replace("research report on", "").replace("research report", "").strip()
            if not self.research_engine:
                from bishu.core.research_engine import ResearchEngine
                from bishu.core.ai_engine import AIEngine
                self.research_engine = ResearchEngine(ai_engine=AIEngine())
            res = self.research_engine.generate_college_report(topic)
            return True, res

        elif "business plan" in action or "compile business" in action:
            topic = action.replace("business plan for", "").replace("business plan on", "").replace("business plan", "").replace("compile business plan", "").strip()
            if not self.research_engine:
                from bishu.core.research_engine import ResearchEngine
                from bishu.core.ai_engine import AIEngine
                self.research_engine = ResearchEngine(ai_engine=AIEngine())
            res = self.research_engine.generate_business_plan(topic)
            return True, res

        elif "slide deck" in action or "ppt presentation" in action or "create slides" in action or "make ppt" in action:
            topic = action.replace("slide deck on", "").replace("slide deck", "").replace("ppt presentation on", "").replace("create slides for", "").replace("make ppt on", "").strip()
            if not self.research_engine:
                from bishu.core.research_engine import ResearchEngine
                from bishu.core.ai_engine import AIEngine
                self.research_engine = ResearchEngine(ai_engine=AIEngine())
            res = self.research_engine.generate_slide_deck(topic)
            return True, res

        # 8. Secure File Vault Commands (Encrypt, Hide/Unhide, Password Lock)
        elif "encrypt directory" in action or "encrypt folder" in action:
            parts = action.split(" password ")
            d_path = parts[0].replace("encrypt directory", "").replace("encrypt folder", "").strip()
            p_word = parts[1].strip() if len(parts) > 1 else "1234"
            if not self.vault_engine:
                from bishu.core.vault_engine import VaultEngine
                self.vault_engine = VaultEngine()
            return True, self.vault_engine.encrypt_directory(d_path, p_word)

        elif "decrypt directory" in action or "decrypt folder" in action:
            parts = action.split(" password ")
            d_path = parts[0].replace("decrypt directory", "").replace("decrypt folder", "").strip()
            p_word = parts[1].strip() if len(parts) > 1 else "1234"
            if not self.vault_engine:
                from bishu.core.vault_engine import VaultEngine
                self.vault_engine = VaultEngine()
            return True, self.vault_engine.decrypt_directory(d_path, p_word)

        elif "hide file" in action or "hide folder" in action or "hide path" in action:
            target = action.replace("hide file", "").replace("hide folder", "").replace("hide path", "").strip()
            if not self.vault_engine:
                from bishu.core.vault_engine import VaultEngine
                self.vault_engine = VaultEngine()
            return True, self.vault_engine.hide_path(target)

        elif "unhide file" in action or "unhide folder" in action or "unhide path" in action:
            target = action.replace("unhide file", "").replace("unhide folder", "").replace("unhide path", "").strip()
            if not self.vault_engine:
                from bishu.core.vault_engine import VaultEngine
                self.vault_engine = VaultEngine()
            return True, self.vault_engine.unhide_path(target)

        elif "lock folder" in action or "password lock" in action:
            parts = action.split(" password ")
            f_path = parts[0].replace("lock folder", "").replace("password lock", "").strip()
            p_word = parts[1].strip() if len(parts) > 1 else "1234"
            if not self.vault_engine:
                from bishu.core.vault_engine import VaultEngine
                self.vault_engine = VaultEngine()
            return True, self.vault_engine.lock_folder(f_path, p_word)

        elif "unlock folder" in action:
            parts = action.split(" password ")
            f_path = parts[0].replace("unlock folder", "").strip()
            p_word = parts[1].strip() if len(parts) > 1 else "1234"
            if not self.vault_engine:
                from bishu.core.vault_engine import VaultEngine
                self.vault_engine = VaultEngine()
            return True, self.vault_engine.unlock_folder(f_path, p_word)

        # 9. Custom Name & User Identity Commands ("call me Mujtaba", "my name is Boss", "mera naam kya hai")
        elif action.startswith("call me ") or action.startswith("my name is ") or "mera naam " in action and ("hai" in action or "rakho" in action):
            name = (
                action.replace("call me ", "")
                .replace("my name is ", "")
                .replace("mera naam ", "")
                .replace(" hai", "")
                .replace(" rakho", "")
                .strip()
                .title()
            )
            if name:
                from bishu.core.sqlite_engine import SQLiteEngine
                db = SQLiteEngine()
                db.set_fact("user_name", name)
                return True, f"Aapka naam {name} save kar liya hai! Ab se main aapko {name} kahkar bulaongi."

        elif any(kw in action for kw in ["what is my name", "mera naam kya hai", "do you know my name", "mera naam batao"]):
            from bishu.core.sqlite_engine import SQLiteEngine
            db = SQLiteEngine()
            u_name = db.get_fact("user_name", default="Boss")
            return True, f"Aapka naam {u_name} hai!"

        # 10. Dynamic NVIDIA Key Setup Command ("set nvidia key nvapi-...")
        elif "nvidia key" in action or "set nvidia" in action or "nvidia api" in action:
            key_str = action.replace("set nvidia key", "").replace("nvidia key", "").replace("set nvidia", "").replace("nvidia api", "").replace("=", "").strip()
            if key_str:
                from bishu.core.memory_engine import MemoryEngine
                from bishu.data.paths import memory_file
                mem = MemoryEngine(memory_file())
                mem.set("NVIDIA_API_KEY", key_str)
                return True, "NVIDIA API Key saved successfully! Laalaa is now connected to NVIDIA Nemotron-3 Ultra 550B."

        # 11. Voice Customization Commands ("change voice to 1", "voice 1", "list voices")
        elif any(kw in action for kw in ["change voice", "voice change", "awaz badlo", "voice 0", "voice 1", "voice 2", "voice 3"]):
            numbers = re.findall(r'\d+', action)
            v_idx = int(numbers[0]) if numbers else 1
            from bishu.core.voice_engine import VoiceEngine
            temp_ve = VoiceEngine()
            res = temp_ve.set_voice_index(v_idx)
            return True, res

        elif any(kw in action for kw in ["list voices", "show voices", "awazen dikhao", "available voices"]):
            from bishu.core.voice_engine import VoiceEngine
            temp_ve = VoiceEngine()
            v_list = temp_ve.get_available_voices()
            v_summary = "Installed System Voices: " + ", ".join([f"[{i}] {name}" for i, name in enumerate(v_list)])
            return True, v_summary

        # 12. Smart Home IoT Commands
        elif any(kw in action for kw in ["light", "pankha", "fan", "ac", "plug", "socket", "ghar ka status", "smart home"]):
            if not self.smarthome_engine:
                from bishu.core.smarthome_engine import SmartHomeEngine
                self.smarthome_engine = SmartHomeEngine()
            sh_success, sh_desc = self.smarthome_engine.process_voice_command(action)
            if sh_success:
                return True, sh_desc

        # 13. Graphify Knowledge Graph Query
        elif any(kw in action for kw in ["graphify", "knowledge graph", "memory graph", "show graph"]):
            if not self.graph_engine:
                from bishu.core.graphify_engine import GraphifyEngine
                self.graph_engine = GraphifyEngine()
            summary = self.graph_engine.get_summary()
            return True, summary

        # 14. Autonomous Self-Correcting Code Generation
        elif action.startswith("code ") or "write code" in action or "make code" in action or "python script" in action:
            spec = action.replace("write code for", "").replace("write code", "").replace("make code for", "").replace("code ", "").strip()
            if not self.code_agent:
                from bishu.core.code_agent import CodeAgent
                self.code_agent = CodeAgent()

            final_code = self.code_agent.self_correcting_loop(spec)
            print("\n✅  ALL TESTS PASS.  Final code ↓\n")
            print(final_code)
            return True, f"Code generated and verified for {spec}. Check terminal for output."

        # 15. Pure Urdu / Hindi Self Introduction
        elif any(kw in action for kw in ["tell me about yourself", "introduce yourself", "who are you", "who r u", "aap kaun hain", "kaun ho tum"]):
            from bishu.core.sqlite_engine import SQLiteEngine
            db = SQLiteEngine()
            u_name = db.get_fact("user_name", default="Boss")
            return True, f"Main Laalaa hoon, aapka shakhsi AI saathi, {u_name}! Main English, Hindi, aur Urdu zubaan mein aapki khidmat ke liye hazir hoon."

        # 16. Pure Urdu / Hindi Greetings
        elif any(kw in action for kw in ["aap kaise hain", "kiya haal hai", "aapka kiya haal hai", "kaise ho", "kaise ho aap", "how are you", "how r u"]):
            from bishu.core.sqlite_engine import SQLiteEngine
            db = SQLiteEngine()
            u_name = db.get_fact("user_name", default="Boss")
            return True, f"Main bilkul khairiyat se hoon, {u_name}! Aap bataiye aapka kya haal hai?"
        elif any(kw in action for kw in ["assalamu alaikum", "assalam o alaikum", "aadaab", "namaste", "hello", "hi laalaa", "hey laalaa"]):
            from bishu.core.sqlite_engine import SQLiteEngine
            db = SQLiteEngine()
            u_name = db.get_fact("user_name", default="Boss")
            return True, f"Walaikum Assalam {u_name}! Main Laalaa hoon, farmaiye main aapki kya khidmat kar sakta hoon?"

        # 17. Camera Selection Commands
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

        # 18. YOLO Vision Objects Scan
        elif any(kw in action for kw in ["yolo", "what do you see", "camera scan", "kya dikh raha hai"]):
            try:
                if not self.vision_ai:
                    from bishu.core.vision_ai import VisionAIEngine
                    self.vision_ai = VisionAIEngine()
                return self.vision_ai.scan_and_detect()
            except Exception as e:
                return False, f"YOLO vision error: {e}"

        # 19. Play Songs on YouTube ("play <song>", "gaana bajao <song>")
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

        # 20. Search Google
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

        # 21. Open YouTube / Chrome / WhatsApp / VS Code
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

        # 22. Application Launchers (Notepad, Calculator)
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

        # 23. Volume & Desktop Controls
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

        # 24. Screenshot
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
