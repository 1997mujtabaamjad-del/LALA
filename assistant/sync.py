"""
Config sync between the Python assistant and the Electron/web app.

The brain server exposes GET/PUT /config; the app maps its settings onto the
Python schema (and back) using the pure tables below, so one pair of API keys
/ light setups / names serves both bodies.
"""

# (python_key, electron_key)
PAIRS = [
    ("name", "name"),
    ("openai_api_key", "openaiKey"),
    ("deepgram_api_key", "deepgramKey"),
    ("elevenlabs_api_key", "elevenlabsKey"),
    ("stt_language", "language"),
    ("save_recordings", "saveRecordings"),
    ("continuous_conversation", "continuousConversation"),
    ("prefer_silero", "preferSilero"),
    ("lights_provider", "lightsProvider"),
    ("hue_ip", "hueIp"),
    ("hue_key", "hueKey"),
    ("ha_url", "haUrl"),
    ("ha_token", "haToken"),
    ("wled_ip", "wledIp"),
]


def to_electron(cfg):
    """Python config → app settings (only keys that are set)."""
    return {js: cfg[py] for py, js in PAIRS if cfg.get(py) is not None}


def to_python(settings):
    """App settings → Python config patch (only keys that are set)."""
    return {py: settings[js] for py, js in PAIRS if settings.get(js) is not None}
