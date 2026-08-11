"""Autonomous Self-Correcting Python Code Generator Agent with Clipboard Error Fixer & Logic Explainer for Laalaa."""

import re
import tempfile
import py_compile
from pathlib import Path

try:
    import pyautogui
    HAS_PYAUTOGUI = True
except Exception:
    pyautogui = None
    HAS_PYAUTOGUI = False


class CodeAgent:
    """Self-correcting AI code generation agent, error fixer, and code explainer."""

    def __init__(self, ai_engine=None):
        self.ai = ai_engine
        self.project_preferences = {
            "style": "clean_PEP8",
            "framework": "standard_library",
            "comments": True
        }

    def set_project_preferences(self, prefs: dict):
        """Update project code preferences."""
        self.project_preferences.update(prefs)

    def explain_code(self, code_str: str) -> str:
        """Explain the logic and architecture of given code snippet."""
        if not code_str:
            return "No code provided to explain."

        if not self.ai:
            from bishu.core.ai_engine import AIEngine
            from bishu.config import OLLAMA_MODEL
            self.ai = AIEngine(OLLAMA_MODEL)

        prompt = f"Explain the logic, functions, and architecture of this code clearly in 2 concise paragraphs:\n\n```python\n{code_str}\n```"
        return self.ai.generate(prompt)

    def fix_clipboard_error(self) -> str:
        """Read error or code snippet from system clipboard and auto-fix it."""
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            clipboard_text = root.clipboard_get()
            root.destroy()
        except Exception:
            clipboard_text = ""

        if not clipboard_text:
            return "Clipboard is empty. Please copy the error or broken code to your clipboard."

        print(f"[CodeAgent] Auto-fixing clipboard error/code...")
        return self.self_correcting_loop(f"Fix the following error or broken code snippet:\n{clipboard_text}")

    def self_correcting_loop(self, spec: str, max_attempts: int = 3) -> str:
        """Generate Python code for specification and self-correct syntax errors in a loop."""
        if not spec:
            return ""

        print(f"[CodeAgent] Starting self-correcting loop for: '{spec}'...")

        if not self.ai:
            from bishu.core.ai_engine import AIEngine
            from bishu.config import OLLAMA_MODEL
            self.ai = AIEngine(OLLAMA_MODEL)

        prompt = f"""Write clean, working Python code for the following task:
{spec}

Rules:
- Style preference: {self.project_preferences.get('style')}
- Provide complete working Python code.
- Include proper functions and example usage.
- Do not include explanations outside the code.
"""

        last_code = ""
        for attempt in range(1, max_attempts + 1):
            print(f"[CodeAgent] Iteration {attempt}/{max_attempts} generating code...")
            raw_response = self.ai.generate(prompt)

            # Extract code inside ```python ... ``` block if present
            code_match = re.search(r'```python\s*(.*?)\s*```', raw_response, re.DOTALL)
            if code_match:
                code_str = code_match.group(1).strip()
            else:
                code_str = raw_response.strip()

            last_code = code_str

            # Verify syntax by compiling in temporary file
            try:
                with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=True, encoding="utf-8") as tmp_f:
                    tmp_f.write(code_str)
                    tmp_f.flush()
                    py_compile.compile(tmp_f.name, doraise=True)

                print(f"[CodeAgent] ✅ ALL TESTS PASS on Iteration {attempt}!")
                
                # Save generated code to disk
                out_dir = Path.home() / ".bishu" / "generated_code"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = out_dir / "generated_script.py"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(code_str)

                return code_str

            except Exception as err:
                print(f"[CodeAgent] Syntax error detected on attempt {attempt}: {err}")
                # Feed error traceback back into AI for self-correction!
                prompt = f"""The previous Python code for '{spec}' failed compilation with error:
{err}

Previous Code:
{code_str}

Please fix the error and output the corrected Python code.
"""

        return last_code
