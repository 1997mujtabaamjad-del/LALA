"""Safety engine to validate and filter high-risk operations."""


class SafetyEngine:
    """Validates actions against security rules and safety policies."""

    BLOCKED_PATTERNS = [
        "rm -rf /",
        "format",
        "del /f /s /q c:\\",
        "reg delete",
        "disable-defender",
        "shutdown",
    ]

    def is_allowed(self, action: str) -> bool:
        """Check if action is safe to execute."""
        if not action:
            return True
        action_lower = action.lower()
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in action_lower:
                return False
        return True
