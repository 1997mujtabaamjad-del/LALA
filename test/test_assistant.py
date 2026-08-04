"""Unit tests for the pure-Python parts of the assistant (no audio deps)."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the assistant's data dir at a temp folder BEFORE importing modules.
from assistant import config  # noqa: E402

config.DATA_DIR = tempfile.mkdtemp(prefix="lala-test-")
config.MEMORY_FILE = os.path.join(config.DATA_DIR, "memory.json")
config.NOTES_FILE = os.path.join(config.DATA_DIR, "notes.json")

from assistant import router  # noqa: E402
from assistant.memory import Memory  # noqa: E402
from assistant import llm  # noqa: E402


class RouterTest(unittest.TestCase):
    def test_open_url(self):
        resp, action = router.handle("open youtube")
        self.assertEqual(action["type"], "url")
        self.assertIn("youtube.com", action["value"])

    def test_open_app_guess(self):
        resp, action = router.handle("open firefox")
        self.assertEqual(action["type"], "app-guess")

    def test_search_wildcard(self):
        resp, action = router.handle("search for lofi beats")
        self.assertIn("q=lofi+beats", action["value"].replace("%20", "+"))

    def test_time(self):
        resp, action = router.handle("what time is it")
        self.assertEqual(action["type"], "speak")
        self.assertIn("It's", resp)

    def test_volume_set(self):
        resp, action = router.handle("set volume to 40 percent")
        self.assertEqual((action["type"], action["op"], action["value"]), ("volume", "set", 40))

    def test_remember_note(self):
        mem = Memory()
        resp, action = router.handle("remember that I like masala chai", mem)
        self.assertIn("masala chai", mem.notes_text())

    def test_not_a_command(self):
        resp, action = router.handle("what is the meaning of life")
        self.assertIsNone(resp)
        self.assertIsNone(action)

    def test_shutdown_needs_confirm(self):
        resp, action = router.handle("shut down computer")
        self.assertTrue(action.get("confirm"))


class MemoryTest(unittest.TestCase):
    def test_history_roundtrip(self):
        mem = Memory()
        mem.add("user", "hello")
        mem.add("assistant", "hi there")
        again = Memory()  # reload from disk
        self.assertEqual(again.recent(2)[-1]["content"], "hi there")

    def test_notes(self):
        mem = Memory()
        mem.add_note("user drinks chai")
        self.assertIn("chai", Memory().notes_text())


class LlmTest(unittest.TestCase):
    def test_mock_provider(self):
        cfg = dict(config.DEFAULTS)
        cfg["llm_provider"] = "mock"
        reply = llm.ask(cfg, None, "hello")
        self.assertIn("offline demo mode", reply)

    def test_system_prompt_includes_notes(self):
        cfg = dict(config.DEFAULTS)
        mem = Memory()
        mem.add_note("likes telugu movies")
        self.assertIn("telugu movies", llm.system_prompt(cfg, mem))


if __name__ == "__main__":
    unittest.main()
