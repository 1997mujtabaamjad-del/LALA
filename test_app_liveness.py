"""Diagnostic test script to verify all Laalaa engines run without freezing or hanging."""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def run_tests():
    print("==================================================")
    print("  Laalaa AI Full Engine Liveness Diagnostic Test  ")
    print("==================================================")

    # 1. Test Memory Engine
    print("\n[1/10] Testing MemoryEngine...")
    from bishu.core.memory_engine import MemoryEngine
    mem = MemoryEngine(Path.home() / ".bishu" / "test_mem.json")
    mem.set("test_key", "test_val")
    assert mem.get("test_key") == "test_val"
    print("  --> MemoryEngine: OK")

    # 2. Test SQLite Engine
    print("\n[2/10] Testing SQLiteEngine...")
    from bishu.core.sqlite_engine import SQLiteEngine
    db = SQLiteEngine(Path.home() / ".bishu" / "test_laalaa.db")
    db.log_chat("User", "Hello test")
    chats = db.get_recent_chats(limit=5)
    assert len(chats) >= 1
    print("  --> SQLiteEngine: OK")

    # 3. Test Audio Engine Buffer
    print("\n[3/10] Testing AudioEngine...")
    from bishu.core.audio_engine import AudioEngine
    audio = AudioEngine()
    buf = audio.get_buffered_audio()
    print(f"  --> AudioEngine Buffer (len={len(buf)}): OK")

    # 4. Test Voice Engine
    print("\n[4/10] Testing VoiceEngine...")
    from bishu.core.voice_engine import VoiceEngine
    voice = VoiceEngine()
    voice.speak("System test active.")
    print("  --> VoiceEngine: OK")

    # 5. Test STT Engine
    print("\n[5/10] Testing STTEngine...")
    from bishu.core.stt_engine import STTEngine
    stt = STTEngine()
    res = stt.transcribe_buffer(buf)
    print(f"  --> STTEngine transcription result: '{res}' (OK)")

    # 6. Test AI Engine
    print("\n[6/10] Testing AIEngine...")
    from bishu.core.ai_engine import AIEngine
    ai = AIEngine()
    reply = ai.generate("Hello")
    print(f"  --> AIEngine generated reply: '{reply}' (OK)")

    # 7. Test Automation Engine
    print("\n[7/10] Testing AutomationEngine...")
    from bishu.core.automation_engine import AutomationEngine
    auto = AutomationEngine()
    ok, desc = auto.run("how are you")
    print(f"  --> AutomationEngine result: ({ok}, '{desc}') (OK)")

    # 8. Test Search Engine
    print("\n[8/10] Testing SearchEngine...")
    from bishu.core.search_engine import SearchEngine
    search = SearchEngine()
    facts = search.search_live("who is Albert Einstein")
    print(f"  --> SearchEngine result length: {len(facts)} chars (OK)")

    # 9. Test LangGraph Engine
    print("\n[9/10] Testing LangGraphEngine...")
    from bishu.core.langgraph_engine import LangGraphEngine
    lg = LangGraphEngine(ai_engine=ai, search_engine=search, automation_engine=auto)
    lg_out = lg.execute("how are you")
    print(f"  --> LangGraphEngine workflow output: '{lg_out}' (OK)")

    # 10. Test Visual Engine
    print("\n[10/10] Testing VisualEngine...")
    from bishu.core.visual_engine import VisualEngine
    ve = VisualEngine()
    ve.set_cpu_ram(15.0, 45.0)
    print("  --> VisualEngine GUI components: OK")

    print("\n==================================================")
    print("  ✅ ALL 10 ENGINES PASSED 100% WITH ZERO FREEZES!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
