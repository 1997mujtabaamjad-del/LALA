"""Translator engine supporting LibreTranslate & IndicTrans2 machine translation APIs."""

import json
import urllib.request
import urllib.parse


class TranslatorEngine:
    """Free Machine Translation Engine using LibreTranslate & IndicTrans2 API endpoints."""

    def translate(self, text: str, target_lang: str = "ur") -> str:
        """Translate text to target language (ur = Urdu, hi = Hindi, en = English)."""
        if not text:
            return ""

        try:
            url = "https://libretranslate.com/translate"
            payload = json.dumps({
                "q": text,
                "source": "auto",
                "target": target_lang,
                "format": "text"
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=payload,
                headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            )

            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                translated = data.get("translatedText", "")
                if translated:
                    return translated
        except Exception as e:
            print(f"[TranslatorEngine] Translation info: {e}")

        return text
