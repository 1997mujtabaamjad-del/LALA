"""
Tool calling (function calling): the LLM's hands.

1. Every existing skill is exposed as a tool schema (OpenAI tools format).
2. chat_with_tools() advertises them to the LLM.
3. When the model emits tool_calls: execute → feed results back → loop.
4. Only the final content is spoken.

Providers: OpenAI + Ollama support the loop; others fall back to plain chat.
"""

import json
import webbrowser
from datetime import datetime
from urllib.parse import quote

from . import calendar_store, lights, llm, weather, websearch

TOOLS = [
    {"type": "function", "function": {
        "name": "get_weather",
        "description": "Current conditions plus a 3-day outlook for a city, "
                       "or the user's location when city is omitted.",
        "parameters": {"type": "object", "properties": {
            "city": {"type": "string", "description": "City name"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "web_search",
        "description": "Look up a fact on the web; returns a short answer text.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "control_lights",
        "description": "Control the user's smart lights (Hue / Home Assistant / WLED).",
        "parameters": {"type": "object", "properties": {
            "op": {"type": "string", "enum": ["on", "off", "set", "color"]},
            "value": {"type": "integer", "description": "brightness percent for op=set"},
            "color": {"type": "string", "description": "color name for op=color"}},
            "required": ["op"]}}},
    {"type": "function", "function": {
        "name": "calendar_add",
        "description": "Add a calendar event; when_text like 'tomorrow at 3pm'.",
        "parameters": {"type": "object", "properties": {
            "title": {"type": "string"}, "when_text": {"type": "string"}},
            "required": ["title", "when_text"]}}},
    {"type": "function", "function": {
        "name": "calendar_list",
        "description": "List the user's upcoming calendar events.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "open_app",
        "description": "Launch a desktop application by name.",
        "parameters": {"type": "object", "properties": {
            "name": {"type": "string"}}, "required": ["name"]}}},
    {"type": "function", "function": {
        "name": "open_url",
        "description": "Open a website in the browser.",
        "parameters": {"type": "object", "properties": {
            "url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {
        "name": "play_music",
        "description": "Play music: opens a YouTube search for the song/artist.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {
        "name": "get_time",
        "description": "The current local time.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "get_date",
        "description": "Today's date.",
        "parameters": {"type": "object", "properties": {}}}},
]

MAX_LOOPS = 4


def execute_tool(name, args, cfg):
    """Run one tool; always returns a string the LLM can read."""
    args = args or {}
    try:
        if name == "get_weather":
            return weather.summary(args.get("city", "")) or "Weather service unreachable."
        if name == "web_search":
            return websearch.answer(args.get("query", "")) or "No instant answer found."
        if name == "control_lights":
            _ok, msg = lights.control(cfg, args.get("op", "on"),
                                      args.get("value"), args.get("color"))
            return msg
        if name == "calendar_add":
            event = calendar_store.add(args.get("title", "event"),
                                       args.get("when_text", ""))
            if not event:
                return "Could not parse a time — ask the user for e.g. 'tomorrow at 3pm'."
            when = datetime.fromisoformat(event["when"])
            return f"Added '{event['title']}' for {when:%A at %I:%M %p}."
        if name == "calendar_list":
            pairs = calendar_store.upcoming()
            if not pairs:
                return "The calendar is clear — nothing scheduled."
            return "Upcoming: " + "; ".join(calendar_store.fmt(p) for p in pairs)
        if name == "open_app":
            from . import router
            router.perform({"type": "app-guess", "value": args.get("name", "")})
            return f"Launched {args.get('name')}."
        if name == "open_url":
            webbrowser.open(args.get("url", ""))
            return f"Opened {args.get('url')}."
        if name == "play_music":
            q = args.get("query", "")
            webbrowser.open(f"https://www.youtube.com/results?search_query={quote(q)}")
            return f"Playing '{q}' on YouTube."
        if name == "get_time":
            return datetime.now().strftime("%I:%M %p")
        if name == "get_date":
            return f"{datetime.now():%A, %B %d, %Y}"
        return f"Unknown tool: {name}"
    except Exception as exc:  # noqa: BLE001 — tools must never crash the loop
        return f"Tool {name} failed: {exc}"


def chat_with_tools(cfg, memory, user_text, provider=None):
    """The agentic loop; final content only is returned for speech."""
    provider = provider or llm.resolve_provider(cfg)
    messages = llm.build_messages(cfg, memory, user_text)
    if provider == "openai" and cfg.get("openai_api_key"):
        return _openai_loop(cfg, messages)
    if provider == "ollama":
        return _ollama_loop(cfg, messages)
    return llm.ask(cfg, memory, user_text, provider)


def _openai_loop(cfg, messages):
    for _ in range(MAX_LOOPS):
        r = requests_post(cfg, messages)
        if r is None:
            break
        msg = r["choices"][0]["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or ""
        for call in calls:
            fn = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            messages.append({"role": "tool", "tool_call_id": call["id"],
                             "content": execute_tool(fn, args, cfg)})
    return messages[-1].get("content") or ""


def _ollama_loop(cfg, messages):
    import requests

    for _ in range(MAX_LOOPS):
        try:
            r = requests.post(cfg["ollama_url"] + "/api/chat",
                              json={"model": cfg["ollama_model"], "messages": messages,
                                    "tools": TOOLS, "stream": False},
                              timeout=60)
            r.raise_for_status()
            msg = r.json()["message"]
        except Exception:  # noqa: BLE001
            break
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            return msg.get("content") or ""
        for call in calls:
            fn = call["function"]["name"]
            args = call["function"].get("arguments") or {}
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}
            messages.append({"role": "tool",
                             "content": execute_tool(fn, args, cfg)})
    return messages[-1].get("content") or ""


def requests_post(cfg, messages):
    import requests

    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {cfg['openai_api_key']}"},
            json={"model": cfg.get("openai_model", "gpt-4o-mini"),
                  "messages": messages, "tools": TOOLS},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()
    except Exception:  # noqa: BLE001
        return None
