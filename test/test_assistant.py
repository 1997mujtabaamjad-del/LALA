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

    def test_stream_mock_yields_single_chunk(self):
        cfg = dict(config.DEFAULTS)
        cfg["llm_provider"] = "mock"
        chunks = list(llm.ask_stream(cfg, None, "hello"))
        self.assertEqual(len(chunks), 1)

    def test_system_prompt_includes_notes(self):
        cfg = dict(config.DEFAULTS)
        mem = Memory()
        mem.add_note("likes telugu movies")
        self.assertIn("telugu movies", llm.system_prompt(cfg, mem))


class TtsTest(unittest.TestCase):
    def test_split_sentences(self):
        from assistant import tts

        sentences, rest = tts.split_sentences("Hello there. How are you? Fine")
        self.assertEqual(sentences, ["Hello there.", "How are you?"])
        self.assertEqual(rest, "Fine")

    def test_split_no_terminator(self):
        from assistant import tts

        sentences, rest = tts.split_sentences("still talking")
        self.assertEqual(sentences, [])
        self.assertEqual(rest, "still talking")


class ServerTest(unittest.TestCase):
    def test_status_and_chat_roundtrip(self):
        import json
        import urllib.request

        from assistant.server import make_server

        cfg = dict(config.DEFAULTS)
        cfg["llm_provider"] = "mock"
        server = make_server(cfg, port=0)  # ephemeral port
        port = server.server_address[1]
        import threading

        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/status", timeout=5) as r:
                self.assertEqual(json.load(r)["name"], cfg["name"])

            req = urllib.request.Request(
                f"http://127.0.0.1:{port}/chat",
                data=json.dumps({"text": "what time is it"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                body = json.load(r)
            self.assertTrue(body["ok"])
            self.assertIn("It's", body["reply"])

            # memory was stored server-side
            self.assertTrue(any(m["role"] == "user" for m in server.assistant.memory.recent(4)))
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
