"""AI Engine supporting MiniMax API and local Ollama with guaranteed warm multilingual spoken responses."""

import json
import urllib.request
import urllib.error
from bishu.config import MINIMAX_API_KEY, MINIMAX_GROUP_ID


class AIEngine:
    """Interface to local Ollama and MiniMax AI APIs."""

    def __init__(self, model_name: str = "llama3.1:latest", api_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url

    def generate(self, prompt: str) -> str:
        """Generate response using MiniMax API if key exists, otherwise local Ollama."""
        try:
            if MINIMAX_API_KEY:
                try:
                    print("[AIEngine] Querying MiniMax Cloud AI API...")
                    url = f"https://api.minimax.chat/v1/text/chatcompletion_v2?GroupID={MINIMAX_GROUP_ID}" if MINIMAX_GROUP_ID else "https://api.minimax.chat/v1/text/chatcompletion_v2"
                    payload = json.dumps({
                        "model": "abab6.5s-chat",
                        "messages": [
                            {"sender_type": "USER", "sender_name": "User", "text": prompt}
                        ]
                    }).encode("utf-8")

                    req = urllib.request.Request(
                        url,
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {MINIMAX_API_KEY}"
                        }
                    )

                    with urllib.request.urlopen(req, timeout=12) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        choices = res_data.get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("text", "")
                            if text:
                                return text.strip()
                except Exception as err:
                    print(f"[AIEngine] MiniMax API info/fallback: {err}")

            # Fallback to local Ollama
            ollama_reply = self._generate_ollama(prompt)
            if ollama_reply:
                return ollama_reply
        except Exception as err:
            print(f"[AIEngine] Exception info: {err}")

        # Always return a polite, warm spoken response so Laalaa NEVER stays silent
        return "Main bilkul khairiyat se hoon! Farmaiye main aapki kya khidmat karoon?"

    def _generate_ollama(self, prompt: str) -> str:
        try:
            model = self._get_available_ollama_model()
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False
            }).encode("utf-8")

            req = urllib.request.Request(
                self.api_url,
                data=payload,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=18) as resp:
                res_data = json.loads(resp.read().decode("utf-8"))
                return res_data.get("response", "").strip()
        except Exception as err:
            print(f"[AIEngine] Ollama info: {err}")
            return ""

    def _get_available_ollama_model(self) -> str:
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                if models:
                    names = [m.get("name") for m in models]
                    for n in names:
                        if self.model_name in n or n in self.model_name:
                            return n
                    return names[0]
        except Exception:
            pass
        return self.model_name
