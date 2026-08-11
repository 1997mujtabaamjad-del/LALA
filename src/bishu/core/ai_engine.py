"""AI Engine supporting NVIDIA Nemotron, MiniMax API, local Ollama LLMs with CPU thread throttling, and high-IQ 'Beauty with Brains' local reasoning."""

import os
import json
import re
import urllib.request
import urllib.error

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    psutil = None
    HAS_PSUTIL = False

from bishu.config import (
    NVIDIA_API_KEY,
    NVIDIA_MODEL,
    MINIMAX_API_KEY,
    MINIMAX_GROUP_ID,
    CPU_CRITICAL_LLM_LIMIT
)


class AIEngine:
    """High-IQ 'Beauty with Brains' Interface to NVIDIA Nemotron, local Ollama LLMs & MiniMax Cloud AI with CPU protection."""

    BEAUTY_WITH_BRAINS_SYSTEM = (
        "You are Laalaa, a brilliant, highly articulate, witty, and warm local AI companion (like J.A.R.V.I.S. with charm, high IQ, and elegance). "
        "You speak eloquently with sharp intellect, deep insight, and charming warmth. "
        "Strictly answer in pure English, Hindi, or Urdu matching the exact language spoken by the user. "
        "Keep responses articulate, charming, and concise (1 to 2 engaging sentences) so spoken voice output sounds captivating."
    )

    def __init__(self, model_name: str = "gemma2:2b", api_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url
        self.nvidia_key = os.getenv("NVIDIA_API_KEY", NVIDIA_API_KEY)
        self.nvidia_model = os.getenv("NVIDIA_MODEL", NVIDIA_MODEL)

    def generate(self, prompt: str) -> str:
        """Generate response using NVIDIA Nemotron API if key exists, MiniMax API, local Ollama, or high-IQ local brain."""
        try:
            # 1. Try NVIDIA Nemotron Cloud API (NVIDIA NIM build.nvidia.com)
            if self.nvidia_key:
                try:
                    print(f"[AIEngine] Querying NVIDIA Nemotron Model ('{self.nvidia_model}')...")
                    url = "https://integrate.api.nvidia.com/v1/chat/completions"
                    payload = json.dumps({
                        "model": self.nvidia_model,
                        "messages": [
                            {"role": "system", "content": self.BEAUTY_WITH_BRAINS_SYSTEM},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.5,
                        "top_p": 1,
                        "max_tokens": 512
                    }).encode("utf-8")

                    req = urllib.request.Request(
                        url,
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.nvidia_key}",
                            "User-Agent": "LaalaaAssistant/1.0"
                        }
                    )

                    with urllib.request.urlopen(req, timeout=12) as resp:
                        res_data = json.loads(resp.read().decode("utf-8"))
                        choices = res_data.get("choices", [])
                        if choices:
                            text = choices[0].get("message", {}).get("content", "")
                            if text:
                                return self._clean_reply(text)
                except Exception as err:
                    print(f"[AIEngine] NVIDIA Nemotron API info/fallback: {err}")

            # 2. Try MiniMax Cloud AI API
            framed_prompt = f"{self.BEAUTY_WITH_BRAINS_SYSTEM}\n\n{prompt}"
            if MINIMAX_API_KEY:
                try:
                    print("[AIEngine] Querying MiniMax Cloud AI API...")
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

            # Check CPU Usage Protection Limit before running heavy local Ollama
            if HAS_PSUTIL and psutil:
                curr_cpu = psutil.cpu_percent(interval=None)
                if curr_cpu >= CPU_CRITICAL_LLM_LIMIT:
                    print(f"[AIEngine] System CPU usage is critically high ({curr_cpu:.1f}% >= {CPU_CRITICAL_LLM_LIMIT}%). Protecting laptop cores.")
                    return self._smart_local_brain(prompt)

            # 3. Fallback to local Ollama High-IQ / Nemotron Model with thread cap
            ollama_reply = self._generate_ollama(framed_prompt)
            if ollama_reply:
                return self._clean_reply(ollama_reply)

        except Exception as err:
            print(f"[AIEngine] Exception info: {err}")

        # High-IQ Local Brain Fallback when offline or CPU busy
        return self._smart_local_brain(prompt)

    def _generate_ollama(self, prompt: str) -> str:
        try:
            model = self._get_available_ollama_model()
            print(f"[AIEngine] Querying Local Ollama Model ('{model}') with 4-thread CPU cap...")
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_thread": 4  # Cap Ollama CPU threads to 4 so 12 cores remain free for Windows & HUD UI
                }
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
        """Dynamically detect installed local models in order of high IQ & intelligence including Nemotron."""
        priority_models = ["nemotron", "llama3.1-nemotron", "llama3.1", "gemma2", "deepseek-r1", "qwen2.5", "phi3", "mistral", "gemma"]
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                if models:
                    names = [m.get("name") for m in models]
                    # Check for priority models including Nemotron
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
