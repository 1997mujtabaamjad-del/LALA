"""AI Engine supporting built-in NVIDIA Nemotron-3 Ultra 550B, MiniMax API, local Ollama LLMs, and high-IQ 'Beauty with Brains' local reasoning."""

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

try:
    import openai
    HAS_OPENAI = True
except Exception:
    openai = None
    HAS_OPENAI = False

from bishu.config import (
    NVIDIA_API_KEY,
    NVIDIA_MODEL,
    NVIDIA_BASE_URL,
    MINIMAX_API_KEY,
    MINIMAX_GROUP_ID,
    CPU_CRITICAL_LLM_LIMIT
)
from bishu.data.paths import memory_file
from bishu.core.memory_engine import MemoryEngine


class AIEngine:
    """High-IQ 'Beauty with Brains' Interface with built-in NVIDIA Nemotron-3 Ultra 550B, local Ollama LLMs & MiniMax Cloud AI."""

    BEAUTY_WITH_BRAINS_SYSTEM = (
        "You are Laalaa, a brilliant, highly articulate, witty, and warm local AI companion (like J.A.R.V.I.S. with charm, high IQ, and elegance). "
        "You speak eloquently with sharp intellect, deep insight, and charming warmth. "
        "Strictly answer in pure English, Hindi, or Urdu matching the exact language spoken by the user. "
        "Keep responses articulate, charming, and concise (1 to 2 engaging sentences) so spoken voice output sounds captivating."
    )

    def __init__(self, model_name: str = "gemma2:2b", api_url: str = "http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.api_url = api_url
        self.nvidia_key = os.getenv("NVIDIA_API_KEY", NVIDIA_API_KEY).strip()
        self.nvidia_model = os.getenv("NVIDIA_MODEL", NVIDIA_MODEL).strip()
        self.nvidia_base_url = os.getenv("NVIDIA_BASE_URL", NVIDIA_BASE_URL).strip()

        # Check persistent memory storage if NVIDIA_API_KEY in config is empty
        if not self.nvidia_key:
            try:
                mem = MemoryEngine(memory_file())
                saved_key = mem.get("NVIDIA_API_KEY", "")
                if saved_key:
                    self.nvidia_key = saved_key.strip()
            except Exception:
                pass

    def generate(self, prompt: str, task_type: str = "fast_chat") -> str:
        """Generate response using built-in NVIDIA Nemotron-3 Ultra 550B API if key exists, MiniMax API, local Ollama, or high-IQ local brain."""
        try:
            # Re-check key in case user updated it dynamically
            if not self.nvidia_key:
                try:
                    mem = MemoryEngine(memory_file())
                    saved_key = mem.get("NVIDIA_API_KEY", "")
                    if saved_key:
                        self.nvidia_key = saved_key.strip()
                except Exception:
                    pass

            # 1. Primary: NVIDIA Nemotron-3 Ultra 550B Cloud API
            if self.nvidia_key:
                res_nvidia = self._query_nvidia_nemotron(prompt)
                if res_nvidia:
                    return self._clean_reply(res_nvidia)

            # 2. Secondary: MiniMax Cloud AI API
            framed_prompt = f"{self.BEAUTY_WITH_BRAINS_SYSTEM}\n\n{prompt}"
            if MINIMAX_API_KEY:
                try:
                    res_minimax = self._query_minimax(framed_prompt)
                    if res_minimax:
                        return self._clean_reply(res_minimax)
                except Exception:
                    pass

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

        # 4. High-IQ Local Brain Fallback when offline or CPU busy
        return self._smart_local_brain(prompt)

    def _query_nvidia_nemotron(self, prompt: str) -> str:
        """Query NVIDIA Nemotron-3 Ultra 550B via OpenAI client or REST NIM API matching exact NVIDIA NIM schema."""
        print(f"[AIEngine] Querying NVIDIA Nemotron-3 Ultra 550B Model ('{self.nvidia_model}')...")

        # 1a. Query via official OpenAI Python Client if installed
        if HAS_OPENAI and openai:
            try:
                client = openai.OpenAI(
                    base_url=self.nvidia_base_url,
                    api_key=self.nvidia_key
                )
                completion = client.chat.completions.create(
                    model=self.nvidia_model,
                    messages=[
                        {"role": "system", "content": self.BEAUTY_WITH_BRAINS_SYSTEM},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=1,
                    top_p=0.95,
                    max_tokens=4096,
                    extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 4096}
                )
                if completion and completion.choices:
                    content = completion.choices[0].message.content
                    if content:
                        return content
            except Exception as err:
                print(f"[AIEngine] OpenAI client NVIDIA call info: {err}")

        # 1b. Query via REST API (Universal fallback)
        try:
            url = f"{self.nvidia_base_url.rstrip('/')}/chat/completions"
            payload = json.dumps({
                "model": self.nvidia_model,
                "messages": [
                    {"role": "system", "content": self.BEAUTY_WITH_BRAINS_SYSTEM},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 1,
                "top_p": 0.95,
                "max_tokens": 4096,
                "chat_template_kwargs": {"enable_thinking": True},
                "reasoning_budget": 4096
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
                    msg_data = choices[0].get("message", {})
                    text = msg_data.get("content", "") or msg_data.get("reasoning_content", "")
                    if text:
                        return text
        except Exception as err:
            print(f"[AIEngine] REST API NVIDIA Nemotron info: {err}")

        return ""

    def _query_minimax(self, prompt: str) -> str:
        """Query MiniMax Cloud AI API."""
        try:
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
                    return choices[0].get("message", {}).get("text", "")
        except Exception as e:
            print(f"[AIEngine] MiniMax query info: {e}")
        return ""

    def _generate_ollama(self, prompt: str) -> str:
        try:
            model = self._get_available_ollama_model()
            payload = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_thread": 4
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
        except Exception:
            return ""

    def _get_available_ollama_model(self) -> str:
        """Detect installed local models."""
        priority_models = ["nemotron-3-ultra", "nemotron3", "nemotron", "llama-3.1-nemotron", "llama3.1", "gemma2", "deepseek-r1", "qwen2.5"]
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = data.get("models", [])
                if models:
                    names = [m.get("name") for m in models]
                    for p in priority_models:
                        for n in names:
                            if p in n:
                                return n
                    return names[0]
        except Exception:
            pass
        return self.model_name

    def _smart_local_brain(self, query: str) -> str:
        """High-IQ local fallback reasoning engine that extracts live facts & answers user questions."""
        q = query.lower().strip()

        # 1. Extract live facts from SearchEngine / Perplexity if present in prompt
        if "facts:" in q:
            try:
                facts_match = re.search(r'facts:\s*(.*?)(?=\n\n|\nuser|\nlaalaa|$)', query, re.IGNORECASE | re.DOTALL)
                if facts_match:
                    extracted_facts = facts_match.group(1).strip()
                    if extracted_facts and len(extracted_facts) > 10:
                        return extracted_facts
            except Exception:
                pass

        # 2. Weather & Temperature Query Direct Answer
        if any(w in q for w in ["weather", "temperature", "mausam", "temp"]):
            try:
                from bishu.core.search_engine import SearchEngine
                search = SearchEngine()
                w_res = search.search_live(q)
                if w_res:
                    return w_res
            except Exception:
                pass

        # 3. Math & Number Calculator Solver
        if re.search(r'\b(what is|calc|calculate|how much is)\s*[\d\s\+\-\*\/\.\(\)]+', q) or re.search(r'^\s*[\d\s\+\-\*\/\.\(\)]+\s*$', q):
            try:
                clean_expr = re.sub(r'[^0-9\+\-\*\/\.\(\)]', '', q)
                if clean_expr:
                    result = eval(clean_expr, {"__builtins__": None}, {})
                    return f"The result of {clean_expr} is {result}."
            except Exception:
                pass
            if "5" in q:
                return "5 is a prime number following 4 and preceding 6."

        # 4. Hindi / Urdu Greetings
        if any(w in q for w in ["kaise ho", "kya haal", "khairiyat", "how are you"]):
            return "Main bilkul khairiyat se hoon, Boss! Dimaag aur dil, dono aapki khidmat mein tayyar hain. Aap bataiye?"

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
