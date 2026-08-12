"""Dynamic Multi-Model Auto-Switcher Agent for automatic model routing based on task complexity, API availability, and system hardware load."""

import os
import json
import urllib.request

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
    CPU_CRITICAL_LLM_LIMIT,
    RAM_CRITICAL_LLM_LIMIT
)
from bishu.data.paths import memory_file
from bishu.core.memory_engine import MemoryEngine


class ModelRouterAgent:
    """Dynamic Multi-Model Auto-Switcher Agent routing queries across Nemotron-3 Ultra 550B, MiniMax, local Ollama, and local fast brain."""

    TASK_CAPABILITY_MAP = {
        "complex_reasoning": ["nvidia_nemotron_3_ultra", "minimax_cloud", "ollama_llama3_1", "smart_local_brain"],
        "code_generation": ["nvidia_nemotron_3_ultra", "ollama_llama3_1", "ollama_qwen2_5", "smart_local_brain"],
        "deep_research": ["nvidia_nemotron_3_ultra", "minimax_cloud", "ollama_gemma2", "smart_local_brain"],
        "fast_chat": ["minimax_cloud", "ollama_gemma2", "nvidia_nemotron_3_ultra", "smart_local_brain"]
    }

    def __init__(self):
        self.nvidia_key = os.getenv("NVIDIA_API_KEY", NVIDIA_API_KEY).strip()
        self.nvidia_model = os.getenv("NVIDIA_MODEL", NVIDIA_MODEL).strip()

    def select_best_model(self, task_type: str = "fast_chat") -> tuple:
        """Select best AI model automatically based on task type, API availability, and CPU/RAM hardware load."""
        # 1. Re-check persistent memory for saved NVIDIA API Key
        if not self.nvidia_key:
            try:
                mem = MemoryEngine(memory_file())
                saved_key = mem.get("NVIDIA_API_KEY", "")
                if saved_key:
                    self.nvidia_key = saved_key.strip()
            except Exception:
                pass

        # 2. Hardware Load Check
        cpu_busy = False
        if HAS_PSUTIL and psutil:
            try:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                if cpu >= CPU_CRITICAL_LLM_LIMIT or ram >= RAM_CRITICAL_LLM_LIMIT:
                    cpu_busy = True
                    print(f"[ModelRouterAgent] High Hardware Load (CPU: {cpu:.1f}%, RAM: {ram:.1f}%). Switching to Cloud API / Local Brain.")
            except Exception:
                pass

        # 3. Task-Based Model Selection
        if task_type in ["code_generation", "deep_research", "complex_reasoning"]:
            if self.nvidia_key:
                print(f"[ModelRouterAgent] Auto-switched to NVIDIA Nemotron-3 Ultra 550B for '{task_type}' task.")
                return "nvidia_nemotron", self.nvidia_model
            elif MINIMAX_API_KEY:
                print(f"[ModelRouterAgent] Auto-switched to MiniMax Cloud AI for '{task_type}' task.")
                return "minimax_cloud", "abab6.5s-chat"
            elif not cpu_busy:
                local_model = self._get_best_local_ollama()
                print(f"[ModelRouterAgent] Auto-switched to Local Ollama ('{local_model}') for '{task_type}' task.")
                return "ollama_local", local_model
            else:
                return "smart_local_brain", "high_iq_fallback"

        # 4. Fast Chat & Everyday Queries
        if MINIMAX_API_KEY:
            return "minimax_cloud", "abab6.5s-chat"
        elif self.nvidia_key:
            return "nvidia_nemotron", self.nvidia_model
        elif not cpu_busy:
            local_model = self._get_best_local_ollama()
            return "ollama_local", local_model

        return "smart_local_brain", "high_iq_fallback"

    def _get_best_local_ollama(self) -> str:
        """Scan local Ollama tags and pick best model."""
        priority_models = ["nemotron-3-ultra", "nemotron3", "nemotron", "llama3.1", "gemma2", "deepseek-r1", "qwen2.5"]
        try:
            req = urllib.request.Request("http://localhost:11434/api/tags")
            with urllib.request.urlopen(req, timeout=2) as resp:
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
        return "gemma2:2b"
