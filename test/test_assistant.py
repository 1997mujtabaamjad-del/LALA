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


class ToolsTest(unittest.TestCase):
    def test_schema_wellformed(self):
        from assistant import tools

        names = [t["function"]["name"] for t in tools.TOOLS]
        self.assertEqual(len(names), len(set(names)))
        for t in tools.TOOLS:
            self.assertEqual(t["type"], "function")
            params = t["function"]["parameters"]
            self.assertEqual(params["type"], "object")

    def test_execute_time_and_date(self):
        from assistant import tools

        cfg = dict(config.DEFAULTS)
        self.assertIn(":", tools.execute_tool("get_time", {}, cfg))
        self.assertIn("2", tools.execute_tool("get_date", {}, cfg))  # year digits

    def test_execute_calendar_roundtrip(self):
        from assistant import calendar_store, tools

        cfg = dict(config.DEFAULTS)
        calendar_store.save([])
        out = tools.execute_tool("calendar_add",
                                 {"title": "standup", "when_text": "tomorrow at 9am"}, cfg)
        self.assertIn("standup", out)
        listed = tools.execute_tool("calendar_list", {}, cfg)
        self.assertIn("standup", listed)

    def test_unknown_tool_safe(self):
        from assistant import tools

        self.assertIn("Unknown tool", tools.execute_tool("nope", {}, dict(config.DEFAULTS)))

    def test_chat_with_tools_mock_falls_back(self):
        from assistant import tools

        cfg = dict(config.DEFAULTS)
        cfg["llm_provider"] = "mock"
        reply = tools.chat_with_tools(cfg, None, "hello")
        self.assertIn("offline demo mode", reply)

    def test_tool_call_accumulation(self):
        from assistant import tools

        slots = {}
        tools._accumulate_tool_call(slots, {"index": 0, "id": "c1",
                                            "function": {"name": "get_time", "arguments": ""}})
        tools._accumulate_tool_call(slots, {"index": 0,
                                            "function": {"arguments": '{"a":'}})
        tools._accumulate_tool_call(slots, {"index": 0, "function": {"arguments": "1}"}})
        call = slots[0]
        self.assertEqual(call["function"]["name"], "get_time")
        import json as _json
        self.assertEqual(_json.loads(call["function"]["arguments"]), {"a": 1})


class MemorySpecTest(unittest.TestCase):
    """The 5-point spec: message list, user/assistant appends, 8–12 window,
    Jarvis system prompt."""

    def test_message_shapes_and_window(self):
        from assistant.memory import Memory

        mem = Memory()
        mem.clear()
        for i in range(15):
            mem.add("user", f"u{i}")
            mem.add("assistant", f"a{i}")
        recent = mem.recent(12)
        self.assertEqual(len(recent), 12)
        self.assertEqual(set(recent[0].keys()), {"role", "content"})
        self.assertEqual(recent[0]["role"], "user")
        self.assertEqual(recent[-1], {"role": "assistant", "content": "a14"})

    def test_build_messages_system_first_then_history_then_user(self):
        from assistant import llm
        from assistant.memory import Memory

        cfg = dict(config.DEFAULTS)
        mem = Memory()
        mem.clear()
        mem.add("user", "hi")
        mem.add("assistant", "hello")
        msgs = llm.build_messages(cfg, mem, "how are you")
        self.assertEqual(msgs[0]["role"], "system")
        self.assertIn("Laala", msgs[0]["content"])  # Laala personality
        self.assertEqual(msgs[1], {"role": "user", "content": "hi"})
        self.assertEqual(msgs[2], {"role": "assistant", "content": "hello"})
        self.assertEqual(msgs[3], {"role": "user", "content": "how are you"})

    def test_persona_configurable(self):
        from assistant import llm

        cfg = dict(config.DEFAULTS)
        cfg["persona"] = "You are {name}, a space pirate."
        self.assertIn("space pirate", llm.system_prompt(cfg, None))

    def test_notes_reach_the_prompt(self):
        from assistant import llm
        from assistant.memory import Memory

        cfg = dict(config.DEFAULTS)
        mem = Memory()
        mem.clear()
        mem.add_note("takes chai at 4pm")
        self.assertIn("chai", llm.system_prompt(cfg, mem))


class GuideTest(unittest.TestCase):
    def test_guide_fallback_static(self):
        from assistant import guide

        cfg = dict(config.DEFAULTS)
        cfg["llm_provider"] = "mock"  # mock reply must be rejected → static tips
        text = guide.generate(cfg)
        self.assertIn("Hey Laala", text)
        self.assertIn("stop listening", text)

    def test_router_guide_phrase(self):
        resp, action = router.handle("how do i use you")
        self.assertEqual(action["type"], "guide")


class LoopTest(unittest.TestCase):
    def _pipeline(self, cfg, think, end_check):
        from assistant import pipeline as pl

        p = pl.Pipeline(cfg, think=think, end_check=end_check)
        p.save_recording = lambda a, t: None
        return p

    def test_turn_thinks_then_stops_on_silence(self):
        import numpy as np

        cfg = dict(config.DEFAULTS)
        calls = []
        p = self._pipeline(cfg, lambda t: calls.append(t), lambda: False)
        audio = np.zeros(8, dtype=np.int16)
        seq = iter([(audio, "hello laala", []), (None, "", [])])
        p.listen = lambda max_seconds=8.0, require_speech=True: next(seq)
        p.turn()
        self.assertEqual(calls, ["hello laala"])

    def test_end_check_breaks_followup_loop(self):
        import numpy as np

        cfg = dict(config.DEFAULTS)
        cfg["continuous_conversation"] = True
        calls = []
        p = self._pipeline(cfg, lambda t: calls.append(t), lambda: len(calls) >= 1)
        audio = np.zeros(8, dtype=np.int16)
        seq = iter([(audio, "one", []), (audio, "two", []), (None, "", [])])
        p.listen = lambda max_seconds=8.0, require_speech=True: next(seq)
        p.turn()
        self.assertEqual(calls, ["one"])


class MilestoneTest(unittest.TestCase):
    def test_full_pipeline_milestone(self):
        from assistant import pipeline

        cfg = dict(config.DEFAULTS)
        cfg["llm_provider"] = "mock"
        results = pipeline.run_milestone(cfg)
        stages = [s for s, _ok, _n in results]
        self.assertEqual(stages, ["wake word", "vad + record", "streaming stt",
                                  "llm", "tts + playback", "recording"])
        for stage, ok, note in results:
            self.assertTrue(ok, f"{stage}: {note}")

    def test_endpoint_on_array(self):
        from assistant import pipeline, vad

        audio = pipeline.synthetic_utterance()
        speech, silence = pipeline.endpoint_on_array(audio, vad.EnergyVAD())
        self.assertGreaterEqual(speech, 400)
        self.assertGreaterEqual(silence, 300)


class VadTest(unittest.TestCase):
    def test_vad_plan(self):
        from assistant import vad

        self.assertEqual(vad.vad_plan(True, True, True), "silero")
        self.assertEqual(vad.vad_plan(True, False, True), "energy")
        self.assertEqual(vad.vad_plan(False, True, True), "energy")

    def test_energy_vad(self):
        import numpy as np

        from assistant import vad

        v = vad.EnergyVAD()
        self.assertFalse(v.speech(np.zeros(1280, dtype=np.int16)))
        loud = (0.3 * np.sin(np.arange(1280) * 0.2) * 32767).astype(np.int16)
        self.assertTrue(v.speech(loud))

    def test_barge_flags(self):
        from assistant import mic

        flags = [False] * 10 + [True] * 6  # 400 ms grace + 480 ms speech @80 ms
        self.assertTrue(mic._barge_flags(flags, 80))
        self.assertFalse(mic._barge_flags([True] * 4 + [False] * 10, 80))
        self.assertFalse(mic._barge_flags([False] * 40, 80))

    def test_silero_real_inference(self):
        import numpy as np

        from assistant import vad

        if not vad.available():
            self.skipTest("onnxruntime/silero-vad not installed")
        v = vad.SileroVAD()
        silence = np.zeros(16000, dtype=np.int16)  # 1 s of silence
        self.assertLess(v.prob(silence), 0.2)


class KeysTest(unittest.TestCase):
    def test_write_env_upsert_and_remove(self):
        from assistant import keys

        path = os.path.join(tempfile.mkdtemp(), ".env")
        with open(path, "w", encoding="utf8") as fh:
            fh.write("# my secrets\nDEEPGRAM_API_KEY=old\nOTHER=keep\n")
        keys.write_env({"DEEPGRAM_API_KEY": "new123", "OPENAI_API_KEY": "sk-1"},
                       path=path)
        text = open(path, encoding="utf8").read()
        self.assertIn("# my secrets", text)
        self.assertIn("DEEPGRAM_API_KEY=new123", text)
        self.assertIn("OPENAI_API_KEY=sk-1", text)
        self.assertIn("OTHER=keep", text)
        self.assertNotIn("old", text)
        keys.write_env(remove=["openai"], path=path)
        text = open(path, encoding="utf8").read()
        self.assertNotIn("OPENAI_API_KEY", text)
        self.assertIn("DEEPGRAM_API_KEY=new123", text)

    def test_mask(self):
        from assistant import keys

        self.assertEqual(keys.mask(""), "—")
        self.assertEqual(keys.mask("short"), "****")
        self.assertTrue(keys.mask("7f795a3500bbb4a67db1").startswith("7f79"))


class EnvTest(unittest.TestCase):
    def test_parse_env(self):
        from assistant import config

        env = config.parse_env("# comment\nDEEPGRAM_API_KEY=abc123\n\n"
                               "OPENAI_API_KEY=\"sk-x\"\nNOVALINE")
        self.assertEqual(env["DEEPGRAM_API_KEY"], "abc123")
        self.assertEqual(env["OPENAI_API_KEY"], "sk-x")
        self.assertNotIn("NOVALINE", env)


class DeepgramTest(unittest.TestCase):
    def test_parse_batch_response(self):
        from assistant import stt

        payload = {"results": {"channels": [
            {"alternatives": [{"transcript": "hello world"}]}]}}
        self.assertEqual(stt.parse_deepgram(payload), "hello world")
        self.assertEqual(stt.parse_deepgram({}), "")

    def test_parse_streaming_message(self):
        from assistant import stt

        interim = {"channel": {"alternatives": [{"transcript": "hello"}]},
                   "is_final": False}
        final = {"channel": {"alternatives": [{"transcript": "hello world"}]},
                 "is_final": True}
        self.assertEqual(stt.parse_dg_message(interim), ("hello", False))
        self.assertEqual(stt.parse_dg_message(final), ("hello world", True))
        self.assertEqual(stt.parse_dg_message({"junk": 1}), ("", False))

    def test_provider_order(self):
        from assistant import stt

        cfg = dict(config.DEFAULTS)
        cfg["stt_provider"] = "auto"
        cfg["deepgram_api_key"] = "k"
        if not stt.local_available():
            self.assertEqual(stt.resolve_provider(cfg), "deepgram")


class RecordingSttTest(unittest.TestCase):
    def test_save_wav_header(self):
        import numpy as np

        from assistant import mic

        path = os.path.join(tempfile.mkdtemp(), "t.wav")
        mic.save_wav(path, np.zeros(1600, dtype=np.int16))
        head = open(path, "rb").read(12)
        self.assertEqual(head[:4], b"RIFF")
        self.assertEqual(head[8:], b"WAVE")

    def test_streaming_transcriber_graceful_without_vosk(self):
        import numpy as np

        from assistant import stt

        cfg = dict(config.DEFAULTS)
        t = stt.StreamingTranscriber(cfg)
        t.feed(np.zeros(1600, dtype=np.int16))
        self.assertIn(t.finish(), ("",))  # no vosk/whisper in CI → empty, no crash


class DeepSkillsTest(unittest.TestCase):
    def test_forecast_sentence(self):
        from assistant import weather

        daily = {"time": ["2026-08-05", "2026-08-06", "2026-08-07"],
                 "weather_code": [0, 61, 3],
                 "temperature_2m_min": [21.4, 20.1, 19.0],
                 "temperature_2m_max": [31.6, 28.2, 27.0]}
        s = weather.forecast_sentence(daily)
        self.assertIn("Today: clear skies, 21–32°", s)
        self.assertIn("Tomorrow: light rain, 20–28°", s)
        self.assertIn("Friday", s)

    def test_ics_roundtrip(self):
        from assistant import calendar_store

        calendar_store.save([])
        calendar_store.add("demo call", "demo call tomorrow at 5pm")
        import tempfile

        path = calendar_store.export_ics(tempfile.mktemp(suffix=".ics"))
        text = open(path, encoding="utf8").read()
        self.assertIn("BEGIN:VEVENT", text)
        self.assertIn("SUMMARY:demo call", text)
        calendar_store.save([])
        added = calendar_store.import_ics(text)
        self.assertEqual(added, 1)
        self.assertEqual(calendar_store.upcoming()[0][1]["title"], "demo call")

    def test_wled_urls(self):
        from assistant import lights

        self.assertEqual(lights.build_wled_url("1.2.3.4", "on"), "http://1.2.3.4/win&T=1")
        self.assertEqual(lights.build_wled_url("1.2.3.4", "off"), "http://1.2.3.4/win&T=0")
        self.assertEqual(lights.build_wled_url("1.2.3.4", "set", 50), "http://1.2.3.4/win&A=127")
        self.assertEqual(lights.build_wled_url("1.2.3.4", "color", None, "blue"),
                         "http://1.2.3.4/win&R=30&G=90&B=255")

    def test_wiki_parse(self):
        from assistant import websearch

        self.assertEqual(websearch.parse_wiki({"extract": "A person."}), "A person.")
        self.assertIsNone(websearch.parse_wiki({"type": "disambiguation", "extract": "x"}))
        self.assertIsNone(websearch.parse_wiki({}))


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
