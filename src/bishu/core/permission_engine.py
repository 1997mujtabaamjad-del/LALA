"""Permission engine for managing action execution privileges."""


class PermissionEngine:
    """Manages permissions and user confirmation settings."""

    def __init__(self):
        self.permissions = {
            "clean_temp": True,
            "read_logs": True,
            "system_notify": True,
        }

    def check_permission(self, action: str) -> bool:
        return self.permissions.get(action, True)
