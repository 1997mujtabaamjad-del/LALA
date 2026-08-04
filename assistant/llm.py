"""
The brain: OpenAI API, local Ollama, or an offline fallback ("mock").
Provider "auto" prefers Ollama (free/local), then OpenAI, then mock.
"""

import json

import requests

TIMEOUT = 45


def _ollama_alive(cfg):
    try:
        r = requests.get(cfg["ollama_url"] + "/api/tags", timeout=1.5)
        return r.ok
    except requests.RequestException:
        return False


def resolve_provider(cfg):
    pref = cfg.get("llm_provider", "auto")
    if pref in ("openai", "ollama", "mock"):
        return pref
    if _ollama_alive(cfg):
        return "ollama"
    if cfg.get("openai_api_key"):
        return "openai"
    return "mock"


def system_prompt(cfg, memory):
    notes = memory.notes_text() if memory else ""
    prompt = (
        f"You are {cfg['name']}, a friendly voice assistant running on the user's desktop. "
        "Answers are spoken aloud, so keep them concise (1-3 sentences) unless the user asks for detail. "
        "You can open apps and websites when asked. Be warm and a little playful."
    )
    if notes:
        prompt += f" Things you remember about the user: {notes}."
    return prompt


def ask(cfg, memory, user_text, provider=None):
    """Return the assistant's reply text."""
    return "".join(ask_stream(cfg, memory, user_text, provider))


def ask_stream(cfg, memory, user_text, provider=None):
    """Yield reply chunks as they arrive (Ollama/OpenAI streaming)."""
    provider = provider or resolve_provider(cfg)
    messages = [{"role": "system", "content": system_prompt(cfg, memory)}]
    messages += memory.recent(cfg.get("memory_window", 12)) if memory else []
    messages.append({"role": "user", "content": user_text})

    if provider == "ollama":
        return _stream_ollama(cfg, messages)
    if provider == "openai":
        return _stream_openai(cfg, messages)
    return iter([_ask_mock(user_text)])


def _stream_ollama(cfg, messages):
    def gen():
        with requests.post(
            cfg["ollama_url"] + "/api/chat",
            json={"model": cfg["ollama_model"], "messages": messages, "stream": True},
            stream=True,
            timeout=TIMEOUT,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                frag = (data.get("message") or {}).get("content")
                if frag:
                    yield frag
    return gen()


def _stream_openai(cfg, messages):
    def gen():
        with requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg['openai_api_key']}"},
            json={"model": cfg["openai_model"], "messages": messages,
                  "max_tokens": 300, "stream": True},
            stream=True,
            timeout=TIMEOUT,
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if not line or not line.startswith(b"data: "):
                    continue
                payload = line[6:].strip()
                if payload == b"[DONE]":
                    break
                try:
                    data = json.loads(payload)
                except ValueError:
                    continue
                delta = (data.get("choices") or [{}])[0].get("delta") or {}
                frag = delta.get("content")
                if frag:
                    yield frag
    return gen()


def _ask_mock(user_text):
    return (
        "I'm in offline demo mode — connect Ollama or add an OpenAI key in Settings "
        f"for real answers. You said: “{user_text}”."
    )


def provider_status(cfg):
    status = {"ollama": _ollama_alive(cfg), "openai": bool(cfg.get("openai_api_key"))}
    status["active"] = resolve_provider(cfg)
    return json.loads(json.dumps(status))
