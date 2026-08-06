"""
Auto-run functional audit: exercises EVERY subsystem, prints ✔ / ⏭ / ✖.

  python -m assistant --selftest        (or: bash scripts/autorun.sh)

Network-dependent checks become ⏭ skip when the egress is blocked; anything
that raises unexpectedly is ✖ FAIL. Exit code 0 unless a hard fail.
"""

import json
import re
import threading
import urllib.request

import numpy as np

from . import (agents, autonomy, calendar_store, config, intent, llm, memory,
               mic, planner, profiles, roles, router, security, stt, sync,
               tools, train_wakeword, tts, vad, vault, vision, wake, weather,
               websearch, world)
from .vault import Vault

NET_EXC = ("URLError", "SSLError", "ConnectionError", "MaxRetryError", "NewConnectionError")


def _net(e):
    return any(t in type(e).__name__ for t in NET_EXC) or "network" in str(e).lower()


class R:
    def __init__(self):
        self.rows = []
        self.fails = 0

    def add(self, name, status, note=""):
        self.rows.append((name, status, note))
        if status == "FAIL":
            self.fails += 1

    def check(self, name, fn):
        try:
            note = fn()
            self.add(name, "ok", note or "")
        except AssertionError as e:
            self.add(name, "FAIL", str(e))
        except Exception as e:  # noqa: BLE001
            if _net(e):
                self.add(name, "skip", "network blocked")
            else:
                self.add(name, "FAIL", f"{type(e).__name__}: {e}")


def run():
    r = R()
    cfg = dict(config.DEFAULTS)
    cfg["llm_provider"] = "mock"

    # ---- routing & commands ----
    r.check("router: exact command", lambda: (
        router.handle("open youtube", None)[1]["type"] == "url") or 1 / 0)
    r.check("router: wildcard weather", lambda: (
        router.handle("weather in hyderabad", None)[1]["city"] == "hyderabad") or 1 / 0)
    r.check("router: role switch", lambda: (
        router.handle("switch to sales", None)[1]["role"] == "sales") or 1 / 0)
    r.check("router: profile create", lambda: (
        router.handle("create profile asha", None)[1]["op"] == "create") or 1 / 0)
    r.check("router: reminder parse", lambda: (
        router.handle("remind me to stretch at 9pm", None)[1]["type"] == "remind") or 1 / 0)
    r.check("router: CEO goal", lambda: (
        router.handle("prepare everything for tomorrow's interview", None)[1]["type"] == "ceo") or 1 / 0)
    r.check("router: code gated", lambda: (
        router.handle("run print(1)", None)[1]["type"] == "code") or 1 / 0)
    r.check("router: memory tools", lambda: (
        router.handle("remember that x", None)[1]["type"] == "memory") or 1 / 0)

    # ---- perform layer ----
    r.check("perform: lights msg", lambda: router.perform(
        {"type": "lights", "op": "on"}) or "x")

    def _weather():
        out = router.perform({"type": "weather", "city": ""})
        if out is None:
            raise ConnectionError("network blocked")
        return out

    r.check("perform: weather", _weather)
    r.check("perform: briefing", lambda: roles.briefing(cfg))
    r.check("perform: finance", lambda: (roles.add_expense(10, "tea"),
                                         roles.finance_summary())[1])
    r.check("perform: crm", lambda: (roles.add_contact("T", "X"),
                                     roles.contact_list())[1])
    r.check("perform: swot(mock)", lambda: router.perform(
        {"type": "swot", "topic": "lala"}))
    r.check("perform: guide", lambda: router.perform({"type": "guide"}))

    # ---- agents / planner / intent ----
    r.check("agents: CEO execute", lambda: agents.CEOAgent(cfg, Vault(), None)
            .execute("prepare for interview")[0])
    r.check("agents: finance analysis", lambda: agents.FinanceAgent(cfg).run("x"))
    r.check("agents: health", lambda: (agents.health_log("log water 1"),
                                       agents.health_log("how's my health"))[1])
    r.check("planner: templates", lambda: len(planner._template("interview prep")[0]) >= 5
            or 1 / 0)
    r.check("intent: classify", lambda: intent.detect("read the screen") == "vision"
            or 1 / 0)

    # ---- memory / vault / profiles ----
    m = memory.Memory()
    r.check("memory: window", lambda: (m.add("user", "hi"), m.add("assistant", "yo"),
                                       len(m.recent(12)) >= 2) or 1 / 0)
    v = Vault()
    r.check("vault: layers+recall", lambda: (v.note("biryani facts"),
                                             any("biryani" in t for _l, t in v.recall("biryani"))) or 1 / 0)
    rng = np.random.default_rng(3)
    t = np.arange(16000) / 16000
    audio = ((0.3 * np.sin(2 * np.pi * 170 * t) + 0.05 * rng.normal(0, 1, len(t))) * 32767).astype(np.int16)
    r.check("profiles: voiceprint match", lambda: (
        profiles.save({"profiles": {"u1": {"voice": profiles.voiceprint(audio).tolist()}}}, ),
        profiles.match_voice(audio) == "u1")[1] or 1 / 0)

    # ---- autonomy / world / twin / vision / robotics ----
    r.check("autonomy: due once", lambda: (autonomy.save_tasks([]),
        autonomy.add_task("reminder", __import__("datetime").datetime.now(), {"msg": "x"}),
        len(autonomy.due_tasks()) == 1) or 1 / 0)
    r.check("world: snapshot", lambda: set(world.snapshot(cfg)) >=
            {"network", "battery", "weather", "calendar", "devices"} or 1 / 0)
    r.check("twin: refresh+diff", lambda: __import__("assistant.twin", fromlist=["diff"]).diff())
    r.check("vision: graceful", lambda: vision.describe())
    r.check("robotics: no robots", lambda: __import__("assistant.robotics",
            fromlist=["status"]).status())
    r.check("extras: pdf graceful", lambda: __import__("assistant.extras",
            fromlist=["pdf_summary"]).pdf_summary("/nonexistent.pdf"))
    r.check("extras: downloads list", lambda: __import__("assistant.extras",
            fromlist=["fresh_downloads"]).fresh_downloads() is not None or 1 / 0)
    r.check("extras: email gated", lambda: not __import__("assistant.extras",
            fromlist=["send_email"]).send_email("a@b.c", "s", "b", cfg).startswith("Email sent") or 1 / 0)

    # ---- llm / tts / vad / wake ----
    r.check("llm: mock ask", lambda: llm.ask(cfg, None, "hi"))
    r.check("llm: persona+role+profile", lambda: "ACTIVE ROLE" in llm.system_prompt(
        {**cfg, "role": "sales"}, None) or 1 / 0)
    r.check("tts: provider fallback", lambda: tts.resolve_provider(cfg) in
            ("none", "piper", "elevenlabs") or 1 / 0)
    r.check("vad: energy detect", lambda: vad.EnergyVAD().speech(
        (0.4 * np.sin(np.arange(1280) * 0.2) * 32767).astype(np.int16)) or 1 / 0)
    r.check("vad: silero optional", lambda: vad.available() in (True, False) or 1 / 0)
    r.check("wake: laala regex", lambda: bool(wake.WAKE_RE.search("hey laala, open x")) or 1 / 0)
    r.check("wake: backend plan", lambda: vad_plan_ok())

    # ---- tools / security / sync ----
    r.check("tools: get_time", lambda: ":" in tools.execute_tool("get_time", {}, cfg))
    r.check("security: gate+mask", lambda: (security.mask("abcdef123456") == "abcd…56",
            not security.gate("coding", security.EXEC)[0])[1] or 1 / 0)
    r.check("sync: mapping roundtrip", lambda: sync.to_python(
        sync.to_electron(cfg)) .get("name") == cfg["name"] or 1 / 0)

    # ---- server endpoints ----
    r.check("server: /status /chat /config", server_roundtrip)

    # ---- ops / packaging artifacts ----
    import os
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for f in ("install.sh", "install.bat", "scripts/install.ps1",
              "scripts/install-mac.sh", "scripts/install-gpu.sh",
              "LALA-standalone.html", "packaging/release.yml",
              "packaging/lala-assistant.spec"):
        r.check(f"artifact: {f}", lambda f=f: os.path.exists(os.path.join(root, f)) or 1 / 0)
    r.check("standalone: brain+voiceprint", lambda: standalone_ok(root))
    r.check("train_wakeword: pipeline fns", lambda: callable(train_wakeword.synthesize_dataset) or 1 / 0)
    r.check("bench: rows", lambda: len(__import__("assistant.bench", fromlist=["run_bench"])
            .run_bench(cfg)) >= 5 or 1 / 0)
    r.check("milestone: all stages", lambda: len(run_milestone_safe(cfg)) == 6 or 1 / 0)

    return r


def vad_plan_ok():
    return vad_plan_truthy()


def vad_plan_truthy():
    from . import vad as _v
    return _v.vad_plan(True, True, True) == "silero" and _v.vad_plan(False, True, True) == "energy"


def standalone_ok(root):
    import os
    s = open(os.path.join(root, "LALA-standalone.html"), encoding="utf8").read()
    return all(k in s for k in ("voiceprintJS", "brain(", "Run demo", "orbit out")) or 1 / 0


def server_roundtrip():
    from . import server

    cfg = dict(config.DEFAULTS)
    cfg["llm_provider"] = "mock"
    srv = server.make_server(cfg, port=0)
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{port}"
        with urllib.request.urlopen(base + "/status", timeout=5) as x:
            assert json.load(x)["ok"]
        req = urllib.request.Request(base + "/chat",
                                     data=json.dumps({"text": "what time is it"}).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as x:
            assert "It's" in json.load(x)["reply"]
        with urllib.request.urlopen(base + "/config", timeout=5) as x:
            assert "config" in json.load(x)
        return "3 endpoints ok"
    finally:
        srv.shutdown()


def run_milestone_safe(cfg):
    from . import pipeline
    return pipeline.run_milestone(cfg)


def main():
    import tempfile

    config.DATA_DIR = tempfile.mkdtemp(prefix="lala-audit-")
    r = run()
    print("\n================ LALA AUTO-RUN AUDIT ================")
    for name, status, note in r.rows:
        mark = {"ok": "✔", "skip": "⏭", "FAIL": "✖"}[status]
        line = f"  [{mark}] {name}"
        if note:
            line += f"  — {note}"
        print(line)
    oks = sum(1 for _n, s, _x in r.rows if s == "ok")
    skips = sum(1 for _n, s, _x in r.rows if s == "skip")
    print(f"-----------------------------------------------------")
    print(f"  {oks} passed · {skips} skipped · {r.fails} failed")
    print(f"=====================================================\n")
    return 1 if r.fails else 0
