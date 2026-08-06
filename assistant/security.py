"""
Security Agent: permission model + secret hygiene + audit log.

Levels: read < write < network < exec < secret.
Every sensitive action must pass `gate()`; confirmations go through the
orchestrator's confirm_fn. Secrets are masked in every log line.
"""

import os
import time

from . import config

READ, WRITE, NETWORK, EXEC, SECRET = "read", "write", "network", "exec", "secret"
ORDER = {READ: 0, WRITE: 1, NETWORK: 2, EXEC: 3, SECRET: 4}

# agent -> max level allowed without confirmation; above => confirm
POLICY = {
    "research": NETWORK,
    "scheduler": WRITE,
    "finance": WRITE,
    "health": WRITE,
    "home": WRITE,
    "vision": READ,
    "coding": READ,        # exec always confirms
    "ceo": WRITE,
}


def mask(secret):
    s = str(secret or "")
    if len(s) <= 8:
        return "****"
    return s[:4] + "…" + s[-2:]


def audit(line):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(os.path.join(config.DATA_DIR, "security.log"), "a", encoding="utf8") as fh:
        fh.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")


def needs_confirm(agent, level):
    cap = POLICY.get(agent, READ)
    return ORDER[level] > ORDER[cap]


def gate(agent, level, confirm_fn=None, detail=""):
    """Returns (allowed, note). Sensitive levels require confirmation."""
    if not needs_confirm(agent, level):
        audit(f"allow {agent}:{level} {detail}")
        return True, ""
    if confirm_fn and confirm_fn(f"{agent} wants {level} access {detail}".strip()):
        audit(f"confirm-ok {agent}:{level} {detail}")
        return True, ""
    audit(f"blocked {agent}:{level} {detail}")
    return False, f"Security: {agent} needs confirmation for {level} access."
