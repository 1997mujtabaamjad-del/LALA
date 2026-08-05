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
        resp, action = router.handle("fly me to the moon please")
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


class SkillsTest(unittest.TestCase):
    def test_weather_describe(self):
        from assistant import weather

        self.assertEqual(weather.describe(61), "light rain")
        self.assertEqual(weather.describe(0), "clear skies")
        self.assertEqual(weather.describe(9999), "cloudy")

    def test_websearch_parse(self):
        from assistant import websearch

        self.assertEqual(websearch.parse_ddg({"AbstractText": "A poet."}), "A poet.")
        self.assertEqual(websearch.parse_ddg({"RelatedTopics": [{"Text": "T."}]}), "T.")
        self.assertIsNone(websearch.parse_ddg({}))

    def test_lights_payloads(self):
        from assistant import lights

        self.assertEqual(lights.build_hue_payload("on"), {"on": True})
        self.assertEqual(lights.build_hue_payload("off"), {"on": False})
        self.assertEqual(lights.build_hue_payload("set", 100), {"on": True, "bri": 254})
        self.assertEqual(lights.build_hue_payload("color", None, "blue"),
                         {"on": True, "hue": 46000, "sat": 254})
        self.assertEqual(lights.build_hue_payload("color", None, "warm"), {"on": True, "ct": 500})

    def test_calendar_add_and_list(self):
        from assistant import calendar_store

        calendar_store.save([])
        event = calendar_store.add("standup", "standup tomorrow at 9am")
        self.assertIsNotNone(event)
        pairs = calendar_store.upcoming()
        self.assertEqual(pairs[0][1]["title"], "standup")
        self.assertIn("9:00 AM", calendar_store.fmt(pairs[0]))

    def test_calendar_needs_time(self):
        from assistant import calendar_store

        self.assertIsNone(calendar_store.parse_when("meeting sometime"))

    def test_router_lights(self):
        resp, action = router.handle("turn on the lights")
        self.assertEqual((action["type"], action["op"]), ("lights", "on"))
        resp, action = router.handle("set lights to 40 percent")
        self.assertEqual(action["value"], 40)

    def test_router_calendar(self):
        resp, action = router.handle("add dentist appointment tomorrow at 3pm")
        self.assertEqual(action["type"], "calendar")
        self.assertEqual(action["title"], "dentist appointment")

    def test_router_websearch(self):
        resp, action = router.handle("who is ada lovelace")
        self.assertEqual((action["type"], action["query"]), ("websearch", "ada lovelace"))

    def test_router_weather(self):
        resp, action = router.handle("weather in hyderabad")
        self.assertEqual((action["type"], action["city"]), ("weather", "hyderabad"))


class WakeBackendTest(unittest.TestCase):
    def test_zoo_word_uses_openwakeword(self):
        from assistant import wake

        self.assertEqual(wake.backend_plan("hey_jarvis", True, False, True), "openwakeword")

    def test_custom_model_preferred_over_vosk(self):
        from assistant import wake

        self.assertEqual(wake.backend_plan("hey_laala", True, True, True),
                         "openwakeword-custom")

    def test_any_phrase_falls_back_to_vosk(self):
        from assistant import wake

        self.assertEqual(wake.backend_plan("hey_laala", False, False, True), "vosk")
        self.assertEqual(wake.backend_plan("hey_laala", True, False, True), "vosk")

    def test_no_backend(self):
        from assistant import wake

        self.assertIsNone(wake.backend_plan("hey_laala", False, False, False))

    def test_wake_regex_matches_laala_variants(self):
        from assistant import wake

        for text in ("hey laala", "hey laala open youtube", "ok laala", "hey la la"):
            self.assertTrue(wake.WAKE_RE.search(text), text)
        self.assertFalse(wake.WAKE_RE.search("open lalaland"))


class ContinuousConversationTest(unittest.TestCase):
    def test_stop_listening_ends_conversation(self):
        resp, action = router.handle("stop listening")
        self.assertEqual(action["type"], "end-conversation")

    def test_followup_phrase(self):
        resp, action = router.handle("that's all for now")
        self.assertEqual(action["type"], "end-conversation")


class BargeInTest(unittest.TestCase):
    def test_silence_never_barges(self):
        from assistant import mic

        self.assertFalse(mic.barge_triggered([0.001] * 60, 80))

    def test_loud_sustained_speech_barges(self):
        from assistant import mic

        seq = [0.001] * 10 + [0.09] * 6  # quiet, then ~480 ms of loud speech
        self.assertTrue(mic.barge_triggered(seq, 80))

    def test_short_blip_ignored(self):
        from assistant import mic

        seq = [0.001] * 10 + [0.09] * 2 + [0.001] * 10
        self.assertFalse(mic.barge_triggered(seq, 80))

    def test_grace_period_protects_utterance_start(self):
        from assistant import mic

        seq = [0.09] * 4 + [0.001] * 20  # energy only inside the grace window
        self.assertFalse(mic.barge_triggered(seq, 80))


class GpuPlanTest(unittest.TestCase):
    def test_stt_plan_cpu_when_no_gpu(self):
        from assistant import gpu

        self.assertEqual(gpu.stt_plan(True, 0), ("cpu", "int8"))

    def test_stt_plan_gpu_fp16(self):
        from assistant import gpu

        self.assertEqual(gpu.stt_plan(True, 1), ("cuda", "float16"))

    def test_stt_plan_prefer_off(self):
        from assistant import gpu

        self.assertEqual(gpu.stt_plan(False, 2), ("cpu", "int8"))

    def test_stt_plan_forced_device(self):
        from assistant import gpu

        self.assertEqual(gpu.stt_plan(True, 0, forced="cuda"), ("cuda", "float16"))
        self.assertEqual(gpu.stt_plan(True, 4, forced="cpu"), ("cpu", "int8"))

    def test_tts_plan(self):
        from assistant import gpu

        self.assertTrue(gpu.tts_plan(True, True))
        self.assertFalse(gpu.tts_plan(True, False))
        self.assertFalse(gpu.tts_plan(False, True))


class TtsProviderTest(unittest.TestCase):
    def test_elevenlabs_selected_when_keyed_and_no_piper(self):
        from assistant import tts

        cfg = dict(config.DEFAULTS)
        cfg["tts_provider"] = "auto"
        cfg["elevenlabs_api_key"] = "test-key"
        if not tts.piper_available():
            self.assertEqual(tts.resolve_provider(cfg), "elevenlabs")

    def test_none_without_any_tts(self):
        from assistant import tts

        cfg = dict(config.DEFAULTS)
        cfg["tts_provider"] = "auto"
        cfg["elevenlabs_api_key"] = ""
        if not tts.piper_available():
            self.assertEqual(tts.resolve_provider(cfg), "none")


class AutostartTest(unittest.TestCase):
    @unittest.skipUnless(__import__("platform").system() == "Linux", "linux-only test")
    def test_linux_desktop_entry(self):
        import platform  # noqa: F401

        from assistant import autostart

        old_home = os.environ.get("HOME")
        tmp = tempfile.mkdtemp(prefix="lala-home-")
        os.environ["HOME"] = tmp
        try:
            path = autostart.install()
            self.assertTrue(os.path.exists(path))
            content = open(path, encoding="utf8").read()
            self.assertIn("[Desktop Entry]", content)
            self.assertIn("-m", content)
            self.assertTrue(autostart.uninstall())
            self.assertFalse(os.path.exists(path))
        finally:
            if old_home is not None:
                os.environ["HOME"] = old_home


if __name__ == "__main__":
    unittest.main()
