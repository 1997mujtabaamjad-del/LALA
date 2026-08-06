"""
Intent detection — the layer between STT and routing/planning.
Classifies utterances so the CEO knows *what kind* of work to dispatch.
"""

import re

RULES = [
    ("goal", re.compile(r"^(prepare|plan|take care of|handle|organize|get .* ready)\b")),
    ("vision", re.compile(r"^(read the screen|what'?s on (my )?screen|look at (the )?screen)")),
    ("world", re.compile(r"^(world status|what'?s my status|system status|status report)")),
    ("twin", re.compile(r"^(what changed|anything new|diff my (desk|environment))")),
    ("health", re.compile(r"^(log |how'?s my (health|sleep|steps|water))")),
    ("finance", re.compile(r"^(add expense|finance summary|budget|spend)")),
    ("schedule", re.compile(r"^(remind me|add .*calendar|watch my|brief me|schedule)")),
    ("research", re.compile(r"^(research|who is|what is|tell me about|search)")),
    ("coding", re.compile(r"^(run |execute |fix |write (a )?(python )?(script|function|code))")),
    ("home", re.compile(r"^(lights|turn (on|off)|robot)")),
    ("command", re.compile(r"^(open |play |set |volume|take a screenshot|switch )")),
    ("memory", re.compile(r"^(remember|recall|what do you (know|remember))")),
    ("smalltalk", re.compile(r"^(hi|hello|hey|thanks|good (morning|night))")),
]


def detect(text):
    t = (text or "").lower().strip()
    for name, rx in RULES:
        if rx.search(t):
            return name
    return "question"
