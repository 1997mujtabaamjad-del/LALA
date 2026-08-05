"""
Spoken user guide: LLM-generated when a brain is available, sensible static
fallback offline. Delivered via TTS (barge-in / "stop talking" for control).
"""

from . import llm

STATIC_TIPS = [
    "Say “Hey Laala” and wait for the beep, then speak your request.",
    "Or hold Space — or tap the mic — and release when you're done.",
    "You can interrupt me any time; just start talking and I'll stop.",
    "After I answer, keep talking — I listen on until you pause, or say “stop listening”.",
    "Try things like “open youtube”, “weather in hyderabad”, “add meeting tomorrow at 3 pm”, or “lights to warm”.",
    "Say “help” for my full command list, and “user guide” to hear this again.",
]

PROMPT = (
    "Write a short spoken user guide — five to seven plain sentences, no markdown, "
    "no quotes — teaching a new user how to talk to you. Cover: the wake word "
    "“Hey Laala”, push-to-talk, that you keep listening for follow-ups, that they "
    "can interrupt you by speaking, two or three example commands (open apps, "
    "weather, calendar, lights), and that “help” lists everything."
)


def generate(cfg, memory=None):
    """Guide text: personalized by the LLM when reachable, static otherwise."""
    try:
        text = llm.ask(cfg, memory, PROMPT)
        if text and len(text) > 80 and "offline demo mode" not in text:
            return text
    except Exception:  # noqa: BLE001
        pass
    return "Here's how to talk to me. " + " ".join(STATIC_TIPS)
