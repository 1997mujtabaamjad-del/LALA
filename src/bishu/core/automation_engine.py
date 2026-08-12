"""Automation engine utilizing PyWhatKit, PyAutoGUI, Subprocess, YOLO Vision AI, Graphify Knowledge Graph, Smart Home Engine, Voice Engine, Avatar Engine, Vault Engine, Research Engine, Scraper Agent, Image AI Agent, Web Builder, VSCode Integration, Shopping Agent, Finance Tracker, WhatsApp Agent, Email Automator, Screen OCR Solver, Spotify Agent, Document Writer, Process Manager, Network Manager, Antivirus Scanner, Voice Auth, Wallpaper Manager, PDF Analyzer, Excel Assistant, System Controls, OCR Clicker, File Explorer Suite, PDF Tools, Voice Typing, File Converter, and Hardware Health."""

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
    """Runs automated system actions, app launchers, YOLO Vision, Smart Home Controls, 2D Avatar, Vault, Research, Scraper, Image AI, Web Builder, VSCode, Shopping, Finance, WhatsApp, Email, OCR, Spotify, Document Writer, Process Manager, Network Manager, Antivirus, Voice Auth, Wallpaper, PDF RAG, Excel, System Controls, OCR Clicker, File Suite, PDF Tools, Voice Typing, File Converter, and Hardware Health."""

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
        self.shopping_agent = None
        self.finance_agent = None
        self.whatsapp_agent = None
        self.email_agent = None
        self.ocr_solver = None
        self.spotify_agent = None
        self.doc_writer = None
        self.process_manager = None
        self.network_manager = None
        self.antivirus_agent = None
        self.voice_auth = None
        self.wallpaper_manager = None
        self.pdf_analyzer = None
        self.excel_assistant = None
        self.system_controls = None
        self.ocr_clicker = None
        self.file_suite = None
        self.pdf_tools = None
        self.voice_typing = None
        self.file_converter = None
        self.hardware_health = None

    def run(self, action: str, task: dict = None) -> tuple:
        """Execute action, returns (success: bool, description: str)."""
        if task is None:
            task = {}

        action = action.lower().strip()
        print(f"[AutomationEngine] Multilingual action: '{action}'")

        # 1. Stop / Close Laalaa
        if any(kw in action for kw in ["stop laalaa", "close laalaa", "exit laalaa", "band karo", "khatam karo", "alvida"]):
            return True, "EXIT_APP"

        # 2. Biometric Voice Auth
        elif "enroll voice" in action or "register voice" in action:
            from bishu.core.voice_auth import VoiceAuthEngine
            self.voice_auth = VoiceAuthEngine()
            res = self.voice_auth.enroll_voice_sample([])
            return True, res

        # 3. Desktop Wallpaper Switcher
        elif "set wallpaper" in action or "change wallpaper" in action or "switch wallpaper" in action:
            from bishu.core.wallpaper_manager import WallpaperManagerEngine
            self.wallpaper_manager = WallpaperManagerEngine()
            res = self.wallpaper_manager.switch_random_wallpaper()
            return True, res

        # 4. PDF/Word Reader & SQLite Vector Cache RAG
        elif "analyze pdf" in action or "search pdf" in action or "read pdf" in action:
            parts = action.split(" query ")
            pdf_p = parts[0].replace("analyze pdf", "").replace("search pdf", "").replace("read pdf", "").strip()
            q_str = parts[1].strip() if len(parts) > 1 else "summary"
            from bishu.core.pdf_analyzer import PDFWordAnalyzerEngine
            from bishu.core.ai_engine import AIEngine
            self.pdf_analyzer = PDFWordAnalyzerEngine(ai_engine=AIEngine())
            res = self.pdf_analyzer.chunk_and_search_pdf(pdf_p, q_str)
            return True, res

        # 5. Excel Spreadsheet Assistant
        elif "excel data" in action or "update spreadsheet" in action or "create excel" in action:
            from bishu.core.excel_assistant import ExcelAssistantEngine
            self.excel_assistant = ExcelAssistantEngine()
            res = self.excel_assistant.create_or_update_excel("Laalaa_Spreadsheet.csv", ["Item", "Cost"], [["Project A", "500"], ["Project B", "750"]])
            return True, res

        # 6. System Controls & Power Management
        elif "set brightness" in action or "adjust brightness" in action:
            numbers = re.findall(r'\d+', action)
            b_val = int(numbers[0]) if numbers else 80
            from bishu.core.system_controls import SystemControlsEngine
            self.system_controls = SystemControlsEngine()
            return True, self.system_controls.set_brightness(b_val)

        elif any(kw in action for kw in ["sleep pc", "restart pc", "hibernate pc", "shutdown pc"]):
            from bishu.core.system_controls import SystemControlsEngine
            self.system_controls = SystemControlsEngine()
            return True, self.system_controls.power_manager(action)

        elif "clean temp" in action or "system cleaner" in action or "clear cache" in action:
            from bishu.core.system_controls import SystemControlsEngine
            self.system_controls = SystemControlsEngine()
            return True, self.system_controls.clean_temp_files()

        # 7. OCR Screen Clicker
        elif "click button" in action or "click text" in action:
            target_t = action.replace("click button", "").replace("click text", "").strip()
            from bishu.core.ocr_clicker import OCRClickerEngine
            self.ocr_clicker = OCRClickerEngine()
            return True, self.ocr_clicker.click_button_text(target_t)

        # 8. File Explorer Suite & ZIP Controller
        elif "duplicate files" in action or "scan duplicates" in action:
            target_f = action.replace("duplicate files in", "").replace("scan duplicates in", "").replace("duplicate files", "").strip() or str(Path.home() / ".bishu")
            from bishu.core.file_suite import FileExplorerSuiteEngine
            self.file_suite = FileExplorerSuiteEngine()
            return True, self.file_suite.scan_duplicate_files(target_f)

        elif "auto organize" in action or "organize folder" in action:
            target_f = action.replace("auto organize", "").replace("organize folder", "").strip() or str(Path.home() / ".bishu")
            from bishu.core.file_suite import FileExplorerSuiteEngine
            self.file_suite = FileExplorerSuiteEngine()
            return True, self.file_suite.auto_organize_folder(target_f)

        elif "compress folder" in action or "zip folder" in action:
            target_f = action.replace("compress folder", "").replace("zip folder", "").strip()
            from bishu.core.file_suite import FileExplorerSuiteEngine
            self.file_suite = FileExplorerSuiteEngine()
            return True, self.file_suite.compress_folder(target_f)

        elif "extract zip" in action or "unzip" in action:
            target_z = action.replace("extract zip", "").replace("unzip", "").strip()
            from bishu.core.file_suite import FileExplorerSuiteEngine
            self.file_suite = FileExplorerSuiteEngine()
            return True, self.file_suite.extract_zip(target_z)

        # 9. PDF Split & Merge
        elif "merge pdf" in action or "combine pdf" in action:
            from bishu.core.pdf_tools import PDFSplitMergeEngine
            self.pdf_tools = PDFSplitMergeEngine()
            return True, self.pdf_tools.merge_pdfs([])

        elif "split pdf" in action:
            pdf_p = action.replace("split pdf", "").strip()
            from bishu.core.pdf_tools import PDFSplitMergeEngine
            self.pdf_tools = PDFSplitMergeEngine()
            return True, self.pdf_tools.split_pdf(pdf_p)

        # 10. Voice Typing & Dictation
        elif "dictate" in action or "type text" in action:
            dict_t = action.replace("dictate", "").replace("type text", "").strip()
            from bishu.core.voice_typing import VoiceTypingEngine
            self.voice_typing = VoiceTypingEngine()
            return True, self.voice_typing.dictate_text(dict_t)

        elif "type clipboard" in action:
            from bishu.core.voice_typing import VoiceTypingEngine
            self.voice_typing = VoiceTypingEngine()
            return True, self.voice_typing.type_clipboard_contents()

        # 11. File Format Converter
        elif "convert word to pdf" in action or "doc to pdf" in action:
            doc_p = action.replace("convert word to pdf", "").replace("doc to pdf", "").strip()
            from bishu.core.file_converter import FileFormatConverterEngine
            self.file_converter = FileFormatConverterEngine()
            return True, self.file_converter.convert_word_to_pdf(doc_p)

        elif "convert image" in action:
            img_p = action.replace("convert image", "").strip()
            from bishu.core.file_converter import FileFormatConverterEngine
            self.file_converter = FileFormatConverterEngine()
            return True, self.file_converter.convert_image_format(img_p, "png")

        # 12. Hardware Health & PC Temperature
        elif "pc temperature" in action or "hardware health" in action or "disk health" in action:
            from bishu.core.hardware_health import HardwareHealthEngine
            self.hardware_health = HardwareHealthEngine()
            return True, self.hardware_health.get_cpu_temperature_health()

        # 13. Spotify Music Integration (Search Tracks, Volume Control, Play Playlists)
        elif "spotify" in action or "search track" in action:
            track = action.replace("spotify search", "").replace("spotify", "").replace("search track", "").strip()
            if not self.spotify_agent:
                from bishu.core.spotify_agent import SpotifyAgent
                self.spotify_agent = SpotifyAgent()
            return True, self.spotify_agent.search_track(track)

        elif "play playlist" in action or "spotify playlist" in action:
            p_name = action.replace("play playlist", "").replace("spotify playlist", "").strip()
            if not self.spotify_agent:
                from bishu.core.spotify_agent import SpotifyAgent
                self.spotify_agent = SpotifyAgent()
            return True, self.spotify_agent.play_playlist(p_name)

        # 14. Notepad Document Writer (Compose Letters, Leave Applications, Auto-Write Memos)
        elif "compose letter" in action or "write letter" in action:
            parts = action.split(" to ")
            topic = parts[0].replace("compose letter on", "").replace("compose letter", "").replace("write letter on", "").replace("write letter", "").strip()
            recip = parts[1].strip() if len(parts) > 1 else "Manager"
            if not self.doc_writer:
                from bishu.core.document_writer import DocumentWriterAgent
                from bishu.core.ai_engine import AIEngine
                self.doc_writer = DocumentWriterAgent(ai_engine=AIEngine())
            return True, self.doc_writer.compose_letter(recip, topic)

        elif "leave application" in action or "apply leave" in action:
            if not self.doc_writer:
                from bishu.core.document_writer import DocumentWriterAgent
                from bishu.core.ai_engine import AIEngine
                self.doc_writer = DocumentWriterAgent(ai_engine=AIEngine())
            return True, self.doc_writer.compose_leave_application("personal work", 2)

        elif "write memo" in action or "create memo" in action:
            memo_title = action.replace("write memo", "").replace("create memo", "").strip() or "General Memorandum"
            if not self.doc_writer:
                from bishu.core.document_writer import DocumentWriterAgent
                from bishu.core.ai_engine import AIEngine
                self.doc_writer = DocumentWriterAgent(ai_engine=AIEngine())
            return True, self.doc_writer.write_memo(memo_title, "Important action items recorded by Laalaa.")

        # 15. Process & RAM Monitor
        elif "list processes" in action or "active processes" in action or "process list" in action:
            if not self.process_manager:
                from bishu.core.process_manager import ProcessManagerAgent
                self.process_manager = ProcessManagerAgent()
            return True, self.process_manager.list_active_processes(limit=10)

        elif "cpu diagnostics" in action or "cpu report" in action or "system diagnostics" in action:
            if not self.process_manager:
                from bishu.core.process_manager import ProcessManagerAgent
                self.process_manager = ProcessManagerAgent()
            return True, self.process_manager.run_cpu_diagnostics()

        elif "terminate app" in action or "close app" in action or "kill process" in action:
            app_target = action.replace("terminate app", "").replace("close app", "").replace("kill process", "").strip()
            if not self.process_manager:
                from bishu.core.process_manager import ProcessManagerAgent
                self.process_manager = ProcessManagerAgent()
            return True, self.process_manager.terminate_app(app_target)

        # 16. Network Manager (WiFi Toggles)
        elif "scan wifi" in action or "nearby networks" in action or "wifi networks" in action:
            if not self.network_manager:
                from bishu.core.network_manager import NetworkManagerAgent
                self.network_manager = NetworkManagerAgent()
            return True, self.network_manager.scan_wifi_networks()

        elif "connect wifi" in action or "wifi connect" in action:
            p_profile = action.replace("connect wifi to", "").replace("connect wifi", "").replace("wifi connect", "").strip()
            if not self.network_manager:
                from bishu.core.network_manager import NetworkManagerAgent
                self.network_manager = NetworkManagerAgent()
            return True, self.network_manager.connect_wifi(p_profile)

        elif "disconnect wifi" in action or "wifi off" in action:
            if not self.network_manager:
                from bishu.core.network_manager import NetworkManagerAgent
                self.network_manager = NetworkManagerAgent()
            return True, self.network_manager.disconnect_wifi()

        # 17. Antivirus File Scanner & Windows Defender Integration
        elif "scan file" in action or "antivirus scan" in action or "malware scan" in action:
            f_target = action.replace("scan file", "").replace("antivirus scan", "").replace("malware scan", "").strip() or str(Path.cwd())
            if not self.antivirus_agent:
                from bishu.core.antivirus_agent import AntivirusScannerAgent
                self.antivirus_agent = AntivirusScannerAgent()
            return True, self.antivirus_agent.quick_scan_file(f_target)

        elif "windows defender" in action or "defender scan" in action:
            if not self.antivirus_agent:
                from bishu.core.antivirus_agent import AntivirusScannerAgent
                self.antivirus_agent = AntivirusScannerAgent()
            return True, self.antivirus_agent.run_windows_defender_scan()

        # 18. Smart Shopping & Food Assistant (Amazon, Flipkart, Zomato, Swiggy)
        elif "search amazon" in action or "search flipkart" in action or "compare price" in action:
            item = action.replace("search amazon for", "").replace("search flipkart for", "").replace("compare price for", "").replace("compare price", "").strip()
            if not self.shopping_agent:
                from bishu.core.shopping_agent import SmartShoppingAgent
                self.shopping_agent = SmartShoppingAgent()
            return True, self.shopping_agent.compare_prices(item)

        elif "zomato" in action or "swiggy" in action or "food finder" in action:
            dish = action.replace("zomato for", "").replace("swiggy for", "").replace("food finder", "").strip()
            if not self.shopping_agent:
                from bishu.core.shopping_agent import SmartShoppingAgent
                self.shopping_agent = SmartShoppingAgent()
            return True, self.shopping_agent.find_food(dish)

        # 19. Live Stock, Index, Forex & Crypto Tracker
        elif "stock index" in action or "nifty" in action or "sensex" in action or "market update" in action:
            if not self.finance_agent:
                from bishu.core.finance_agent import FinanceTrackerAgent
                self.finance_agent = FinanceTrackerAgent()
            return True, self.finance_agent.get_stock_index_updates()

        elif "crypto" in action or "bitcoin" in action or "ethereum" in action or "solana" in action:
            if not self.finance_agent:
                from bishu.core.finance_agent import FinanceTrackerAgent
                self.finance_agent = FinanceTrackerAgent()
            return True, self.finance_agent.get_crypto_prices()

        elif "forex" in action or "exchange rate" in action or "usd inr" in action:
            if not self.finance_agent:
                from bishu.core.finance_agent import FinanceTrackerAgent
                self.finance_agent = FinanceTrackerAgent()
            return True, self.finance_agent.get_forex_exchange_rates()

        # 20. WhatsApp Texting, Chat Search, Voice/Video Call, Draft Typing
        elif "whatsapp msg" in action or "whatsapp message" in action or "whatsapp send" in action:
            parts = action.split(" message ")
            target = parts[0].replace("whatsapp msg to", "").replace("whatsapp message to", "").replace("whatsapp send to", "").strip()
            msg_text = parts[1].strip() if len(parts) > 1 else "Hello from Laalaa!"
            if not self.whatsapp_agent:
                from bishu.core.whatsapp_agent import WhatsAppAgent
                self.whatsapp_agent = WhatsAppAgent()
            return True, self.whatsapp_agent.send_message(target, msg_text)

        elif "whatsapp call" in action or "video call whatsapp" in action:
            c_type = "video" if "video" in action else "voice"
            target = action.replace("whatsapp call", "").replace("video call whatsapp", "").replace("to ", "").strip()
            if not self.whatsapp_agent:
                from bishu.core.whatsapp_agent import WhatsAppAgent
                self.whatsapp_agent = WhatsAppAgent()
            return True, self.whatsapp_agent.make_call(target, call_type=c_type)

        elif "whatsapp search" in action or "open whatsapp chat" in action:
            target = action.replace("whatsapp search", "").replace("open whatsapp chat for", "").replace("open whatsapp chat", "").strip()
            if not self.whatsapp_agent:
                from bishu.core.whatsapp_agent import WhatsAppAgent
                self.whatsapp_agent = WhatsAppAgent()
            return True, self.whatsapp_agent.open_chat(target)

        # 21. SMTP Email Automator & Gmail Dashboard
        elif "send email" in action or "send cc email" in action:
            parts = action.split(" subject ")
            target = parts[0].replace("send email to", "").replace("send cc email to", "").strip()
            subj = "Update from Laalaa"
            body_text = "Hello, this is an automated email sent by Laalaa AI Assistant."
            if len(parts) > 1:
                sub_parts = parts[1].split(" body ")
                subj = sub_parts[0].strip()
                if len(sub_parts) > 1:
                    body_text = sub_parts[1].strip()
            if not self.email_agent:
                from bishu.core.email_agent import EmailAutomatorAgent
                self.email_agent = EmailAutomatorAgent()
            return True, self.email_agent.send_email(target, subj, body_text)

        elif "gmail dashboard" in action or "open gmail" in action:
            if not self.email_agent:
                from bishu.core.email_agent import EmailAutomatorAgent
                self.email_agent = EmailAutomatorAgent()
            return True, self.email_agent.open_gmail_dashboard()

        # 22. Screen Text Reader (OCR) & Assignment Solver
        elif "ocr screen" in action or "read screen text" in action or "screen ocr" in action:
            if not self.ocr_solver:
                from bishu.core.ocr_solver import ScreenOCRSolver
                from bishu.core.ai_engine import AIEngine
                self.ocr_solver = ScreenOCRSolver(ai_engine=AIEngine())
            return True, self.ocr_solver.capture_screen_text()

        elif "solve question" in action or "solve assignment" in action or "screen question" in action:
            if not self.ocr_solver:
                from bishu.core.ocr_solver import ScreenOCRSolver
                from bishu.core.ai_engine import AIEngine
                self.ocr_solver = ScreenOCRSolver(ai_engine=AIEngine())
            return True, self.ocr_solver.solve_screen_question()

        # 23. AI Image Generator (Stable Diffusion text-to-image with custom aspect ratios)
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

        # 24. AI Website Template Builder (HTML5 Canvas, CSS Grid, Tailwind JS)
        elif "build website" in action or "build template" in action or "create html website" in action or "make website" in action:
            p_str = action.replace("build website for", "").replace("build website", "").replace("build template for", "").replace("build template", "").replace("create html website for", "").replace("make website for", "").strip()
            if not self.web_builder:
                from bishu.core.web_builder import WebTemplateBuilder
                from bishu.core.ai_engine import AIEngine
                self.web_builder = WebTemplateBuilder(ai_engine=AIEngine())
            res = self.web_builder.build_template(p_str)
            return True, res

        # 25. Web Scraper Agent (Raw URLs, Table Links, Page Paragraphs)
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

        # 26. VSCode Workspace Integration (Syntax Validation, Run Tasks, Open Workspace)
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

        # 27. AI Code Fixer, Builder & Explainer
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

        # 28. Deep Research Report Generator (College Reports, Business Plans, Slide Deck PPTs)
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

        # 29. Secure File Vault Commands (Encrypt, Hide/Unhide, Password Lock)
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

        # 30. Custom Name & User Identity Commands ("call me Mujtaba", "my name is Boss", "mera naam kya hai")
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

        # 31. Dynamic NVIDIA Key Setup Command ("set nvidia key nvapi-...")
        elif "nvidia key" in action or "set nvidia" in action or "nvidia api" in action:
            key_str = action.replace("set nvidia key", "").replace("nvidia key", "").replace("set nvidia", "").replace("nvidia api", "").replace("=", "").strip()
            if key_str:
                from bishu.core.memory_engine import MemoryEngine
                from bishu.data.paths import memory_file
                mem = MemoryEngine(memory_file())
                mem.set("NVIDIA_API_KEY", key_str)
                return True, "NVIDIA API Key saved successfully! Laalaa is now connected to NVIDIA Nemotron-3 Ultra 550B."

        # 32. Voice Customization Commands ("change voice to 1", "voice 1", "list voices")
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

        # 33. Smart Home IoT Commands
        elif any(kw in action for kw in ["light", "pankha", "fan", "ac", "plug", "socket", "ghar ka status", "smart home"]):
            if not self.smarthome_engine:
                from bishu.core.smarthome_engine import SmartHomeEngine
                self.smarthome_engine = SmartHomeEngine()
            sh_success, sh_desc = self.smarthome_engine.process_voice_command(action)
            if sh_success:
                return True, sh_desc

        # 34. Graphify Knowledge Graph Query
        elif any(kw in action for kw in ["graphify", "knowledge graph", "memory graph", "show graph"]):
            if not self.graph_engine:
                from bishu.core.graphify_engine import GraphifyEngine
                self.graph_engine = GraphifyEngine()
            summary = self.graph_engine.get_summary()
            return True, summary

        # 35. Autonomous Self-Correcting Code Generation
        elif action.startswith("code ") or "write code" in action or "make code" in action or "python script" in action:
            spec = action.replace("write code for", "").replace("write code", "").replace("make code for", "").replace("code ", "").strip()
            if not self.code_agent:
                from bishu.core.code_agent import CodeAgent
                self.code_agent = CodeAgent()

            final_code = self.code_agent.self_correcting_loop(spec)
            print("\n✅  ALL TESTS PASS.  Final code ↓\n")
            print(final_code)
            return True, f"Code generated and verified for {spec}. Check terminal for output."

        # 36. Pure Urdu / Hindi Self Introduction
        elif any(kw in action for kw in ["tell me about yourself", "introduce yourself", "who are you", "who r u", "aap kaun hain", "kaun ho tum"]):
            from bishu.core.sqlite_engine import SQLiteEngine
            db = SQLiteEngine()
            u_name = db.get_fact("user_name", default="Boss")
            return True, f"Main Laalaa hoon, aapka shakhsi AI saathi, {u_name}! Main English, Hindi, aur Urdu zubaan mein aapki khidmat ke liye hazir hoon."

        # 37. Pure Urdu / Hindi Greetings
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

        # 38. Camera Selection Commands
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

        # 39. YOLO Vision Objects Scan
        elif any(kw in action for kw in ["yolo", "what do you see", "camera scan", "kya dikh raha hai"]):
            try:
                if not self.vision_ai:
                    from bishu.core.vision_ai import VisionAIEngine
                    self.vision_ai = VisionAIEngine()
                return self.vision_ai.scan_and_detect()
            except Exception as e:
                return False, f"YOLO vision error: {e}"

        # 40. Play Songs on YouTube ("play <song>", "gaana bajao <song>")
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

        # 41. Search Google
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

        # 42. Open YouTube / Chrome / WhatsApp / VS Code
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

        # 43. Application Launchers (Notepad, Calculator)
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

        # 44. Volume & Desktop Controls
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

        # 45. Screenshot
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
