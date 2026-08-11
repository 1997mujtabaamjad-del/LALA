"""Diagnostic test script to verify all 22 Laalaa engines run without freezing or hanging."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_tests():
    print("==================================================")
    print("  Laalaa AI Full 22-Engine Liveness Diagnostic Test ")
    print("==================================================")

    # 1. Test Memory Engine
    print("\n[1/22] Testing MemoryEngine...")
    from bishu.core.memory_engine import MemoryEngine
    mem = MemoryEngine(Path.home() / ".bishu" / "test_mem.json")
    mem.set("test_key", "test_val")
    assert mem.get("test_key") == "test_val"
    print("  --> MemoryEngine: OK")

    # 2. Test SQLite Engine
    print("\n[2/22] Testing SQLiteEngine...")
    from bishu.core.sqlite_engine import SQLiteEngine
    db = SQLiteEngine(Path.home() / ".bishu" / "test_laalaa.db")
    db.log_chat("User", "Hello test")
    chats = db.get_recent_chats(limit=5)
    assert len(chats) >= 1
    print("  --> SQLiteEngine: OK")

    # 3. Test Audio Engine Buffer
    print("\n[3/22] Testing AudioEngine...")
    from bishu.core.audio_engine import AudioEngine
    audio = AudioEngine()
    buf = audio.get_buffered_audio()
    print(f"  --> AudioEngine Buffer (len={len(buf)}): OK")

    # 4. Test Voice Engine
    print("\n[4/22] Testing VoiceEngine...")
    from bishu.core.voice_engine import VoiceEngine
    voice = VoiceEngine()
    voice.speak("System test active.")
    print("  --> VoiceEngine: OK")

    # 5. Test STT Engine
    print("\n[5/22] Testing STTEngine...")
    from bishu.core.stt_engine import STTEngine
    stt = STTEngine()
    res = stt.transcribe_buffer(buf)
    print(f"  --> STTEngine transcription result: '{res}' (OK)")

    # 6. Test AI Engine
    print("\n[6/22] Testing AIEngine...")
    from bishu.core.ai_engine import AIEngine
    ai = AIEngine()
    reply = ai.generate("Hello")
    print(f"  --> AIEngine generated reply: '{reply}' (OK)")

    # 7. Test Automation Engine
    print("\n[7/22] Testing AutomationEngine...")
    from bishu.core.automation_engine import AutomationEngine
    auto = AutomationEngine()
    ok, desc = auto.run("how are you")
    print(f"  --> AutomationEngine result: ({ok}, '{desc}') (OK)")

    # 8. Test Search Engine
    print("\n[8/22] Testing SearchEngine...")
    from bishu.core.search_engine import SearchEngine
    search = SearchEngine()
    facts = search.search_live("who is Albert Einstein")
    print(f"  --> SearchEngine result length: {len(facts)} chars (OK)")

    # 9. Test LangGraph Engine
    print("\n[9/22] Testing LangGraphEngine...")
    from bishu.core.langgraph_engine import LangGraphEngine
    lg = LangGraphEngine(ai_engine=ai, search_engine=search, automation_engine=auto)
    lg_out = lg.execute("how are you")
    print(f"  --> LangGraphEngine workflow output: '{lg_out}' (OK)")

    # 10. Test Visual Engine
    print("\n[10/22] Testing VisualEngine...")
    from bishu.core.visual_engine import VisualEngine
    ve = VisualEngine()
    ve.set_cpu_ram(15.0, 45.0)
    print("  --> VisualEngine GUI components: OK")

    # 11. Test Avatar Engine
    print("\n[11/22] Testing AvatarEngine...")
    from bishu.core.avatar_engine import AvatarWindow
    av = AvatarWindow()
    av.set_expression("HAPPY")
    av.set_gesture("WAVE")
    av.set_vocal_sync(0.5)
    print("  --> AvatarEngine (Live 2D Avatar + 8 Gestures + Vocal Lip-Sync): OK")

    # 12. Test Vault Engine
    print("\n[12/22] Testing VaultEngine...")
    from bishu.core.vault_engine import VaultEngine
    vault = VaultEngine(Path.home() / ".bishu" / "test_vault_meta.json")
    v_res = vault.lock_folder(str(Path.home() / ".bishu" / "test_folder"), "1234")
    print(f"  --> VaultEngine result: '{v_res}' (OK)")

    # 13. Test Research Engine
    print("\n[13/22] Testing ResearchEngine...")
    from bishu.core.research_engine import ResearchEngine
    re_engine = ResearchEngine(ai_engine=ai)
    r_res = re_engine.generate_college_report("Quantum Computing")
    print(f"  --> ResearchEngine result: '{r_res}' (OK)")

    # 14. Test Web Scraper Agent
    print("\n[14/22] Testing WebScraperAgent...")
    from bishu.core.scraper_agent import WebScraperAgent
    scraper = WebScraperAgent()
    s_res = scraper.read_raw_url("https://example.com")
    print(f"  --> WebScraperAgent result: '{s_res[:60]}...' (OK)")

    # 15. Test Image AI Agent
    print("\n[15/22] Testing ImageAIAgent...")
    from bishu.core.image_agent import ImageAIAgent
    img_agent = ImageAIAgent()
    i_res = img_agent.generate_image("A cyberpunk city", aspect_ratio="16:9")
    print(f"  --> ImageAIAgent result: '{i_res}' (OK)")

    # 16. Test Web Template Builder
    print("\n[16/22] Testing WebTemplateBuilder...")
    from bishu.core.web_builder import WebTemplateBuilder
    builder = WebTemplateBuilder(ai_engine=ai)
    w_res = builder.build_template("Cyberpunk Portfolio")
    print(f"  --> WebTemplateBuilder result: '{w_res}' (OK)")

    # 17. Test VSCode Integration
    print("\n[17/22] Testing VSCodeIntegration...")
    from bishu.core.vscode_agent import VSCodeIntegration
    vscode = VSCodeIntegration()
    v_syntax = vscode.validate_syntax(str(Path(__file__)))
    print(f"  --> VSCodeIntegration result: '{v_syntax}' (OK)")

    # 18. Test Shopping Agent
    print("\n[18/22] Testing SmartShoppingAgent...")
    from bishu.core.shopping_agent import SmartShoppingAgent
    shopping = SmartShoppingAgent()
    sh_res = shopping.compare_prices("Laptop Stand")
    print(f"  --> SmartShoppingAgent result: '{sh_res}' (OK)")

    # 19. Test Finance Tracker Agent
    print("\n[19/22] Testing FinanceTrackerAgent...")
    from bishu.core.finance_agent import FinanceTrackerAgent
    finance = FinanceTrackerAgent()
    f_res = finance.get_crypto_prices()
    print(f"  --> FinanceTrackerAgent result: '{f_res}' (OK)")

    # 20. Test WhatsApp Agent
    print("\n[20/22] Testing WhatsAppAgent...")
    from bishu.core.whatsapp_agent import WhatsAppAgent
    wa = WhatsAppAgent()
    wa_res = wa.type_message_draft("Hello Boss!")
    print(f"  --> WhatsAppAgent result: '{wa_res}' (OK)")

    # 21. Test Email Automator Agent
    print("\n[21/22] Testing EmailAutomatorAgent...")
    from bishu.core.email_agent import EmailAutomatorAgent
    email_ag = EmailAutomatorAgent()
    em_res = email_ag.open_gmail_dashboard()
    print(f"  --> EmailAutomatorAgent result: '{em_res}' (OK)")

    # 22. Test Screen OCR Solver
    print("\n[22/22] Testing ScreenOCRSolver...")
    from bishu.core.ocr_solver import ScreenOCRSolver
    ocr_ag = ScreenOCRSolver(ai_engine=ai)
    ocr_res = ocr_ag.capture_screen_text()
    print(f"  --> ScreenOCRSolver result: '{ocr_res[:60]}...' (OK)")

    print("\n==================================================")
    print("  ✅ ALL 22 ENGINES PASSED 100% WITH ZERO FREEZES!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
