"""AI Engine supporting MiniMax API, local Ollama LLMs, and high-IQ 'Beauty with Brains' local reasoning."""

import json
import re
import urllib.request
import urllib.error
from bishu.config import MINIMAX_API_KEY, MINIMAX_GROUP_ID


class AIEngine:
    """High-IQ 'Beauty with Brains' Interface to local Ollama LLMs & MiniMax Cloud AI."""

    BEAUTY_WITH_BRAINS_SYSTEM = (
        "You are Laalaa, a brilliant, highly articulate, witty, and warm local AI companion (like J.A.R.V.I.S. with charm, high IQ, and elegance). "
        "You speak eloquently with sharp intellect, deep insight, and charming warmth. "
        "Strictly answer in pure English, Hindi, or Urdu matching the exact language spoken by the user. "
        "Keep responses articulate, charming, and concise (1 to 2 engaging sentences) so spoken voice output sounds captivating."
    )

    def __init__(self, model_name: str = "gemma2:2b", api_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url

    def generate(self, prompt: str) -> str:
        """Generate response using MiniMax API if key exists, otherwise local Ollama or high-IQ local brain."""
        try:
            # Framing prompt with 'Beauty with Brains' persona
            framed_prompt = f"{self.BEAUTY_WITH_BRAINS_SYSTEM}\n\n{prompt}"

            if MINIMAX_API_KEY:
                try:
                    print("[AIEngine] Querying MiniMax Cloud AI API (Beauty with Brains Persona)...")
                    url = f"https://api.minimax.chat/v1/text/chatcompletion_v2?GroupID={MINIMAX_GROUP_ID}" if MINIMAX_GROUP_ID else "https://api.minimax.chat/v1/text/chatcompletion_v2"
                    payload = json.dumps({
                        "model": "abab6.5s-chat",
                        "messages": [
                            {"sender_type": "USER", "sender_name": "User", "text": framed_prompt}
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
                                return self._clean_reply(text)
                except Exception as err:
                    print(f"[AIEngine] MiniMax API info/fallback: {err}")

            # Fallback to local Ollama High-IQ Model
            ollama_reply = self._generate_ollama(framed_prompt)
            if ollama_reply:
                return self._clean_reply(ollama_reply)

        except Exception as err:
            print(f"[AIEngine] Exception info: {err}")

        # High-IQ Local Brain Fallback when offline
        return self._smart_local_brain(prompt)

    def _generate_ollama(self, prompt: str) -> str:
        try:
            model = self._get_available_ollama_model()
            print(f"[AIEngine] Querying Local Ollama LLM Model ('{model}')...")
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
        """Dynamically detect installed local models in order of high IQ & intelligence."""
        priority_models = ["llama3.1", "gemma2", "deepseek-r1", "qwen2.5", "phi3", "mistral", "gemma"]
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                if models:
                    names = [m.get("name") for m in models]
                    # Check for priority models
                    for p in priority_models:
                        for n in names:
                            if p in n:
                                return n
                    return names[0]
        except Exception:
            pass
        return self.model_name

    def _smart_local_brain(self, query: str) -> str:
        """High-IQ local fallback reasoning engine for charming, intelligent answers."""
        q = query.lower().strip()

        # Hindi / Urdu Greetings
        if any(w in q for w in ["kaise ho", "kya haal", "khairiyat", "how are you"]):
            return "Main bilkul khairiyat se hoon! Dimaag aur dil, dono aapki khidmat mein tayyar hain. Aap bataiye?"

        if any(w in q for w in ["who are you", "tum kaun ho", "aap kaun hain"]):
            return "Main Laalaa hoon — beauty with brains! Aapki shakhsi AI saathi, jo hamesha ek qadam aage sochti hai."

        if any(w in q for w in ["hello", "hi", "assalam", "aadaab", "namaste"]):
            return "Walaikum Assalam! Main hazir hoon. Aaj hum milkar kya bada kaam karne wale hain?"

        return "Main bilkul khairiyat se hoon! Har mushkil ka hal aur har sawal ka jawab mere pas hai. Farmaiye?"

    def _clean_reply(self, text: str) -> str:
        """Clean markdown formatting and tags for natural speech synthesis."""
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        text = re.sub(r'[*_#`~]', '', text)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return " ".join(lines[:2]).strip()
