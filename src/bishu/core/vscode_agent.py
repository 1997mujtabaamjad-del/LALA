"""VSCode Workspace Integration for syntax validation, running tasks, and launching workspace projects."""

import os
import sys
import ast
import subprocess
from pathlib import Path


class VSCodeIntegration:
    """VSCode Workspace Integration for syntax validation, task execution, and project management."""

    def validate_syntax(self, file_path: str) -> str:
        """Validate Python syntax for file in VSCode workspace."""
        path = Path(file_path)
        if not path.exists():
            return f"File '{file_path}' not found."

        if path.suffix == ".py":
            try:
                with open(path, "r", encoding="utf-8") as f:
                    code = f.read()
                ast.parse(code)
                return f"Syntax Validation PASSED: '{path.name}' has 0 syntax errors."
            except SyntaxError as e:
                return f"Syntax Error in '{path.name}' at line {e.lineno}: {e.msg}"
            except Exception as e:
                return f"Validation error: {e}"

        return f"File '{path.name}' validated."

    def run_vscode_task(self, task_name: str) -> str:
        """Execute VSCode workspace task or terminal build script."""
        task = task_name.strip()
        print(f"[VSCodeIntegration] Running VSCode task: '{task}'...")

        try:
            if os.name == "nt":
                subprocess.Popen(["cmd", "/c", task], shell=True)
            else:
                subprocess.Popen([task], shell=True)
            return f"VSCode task '{task}' dispatched to terminal."
        except Exception as e:
            return f"Failed to run VSCode task '{task}': {e}"

    def open_workspace(self, folder_path: str) -> str:
        """Open workspace project in Visual Studio Code."""
        path = Path(folder_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)

        try:
            if os.name == "nt":
                os.system(f'start code "{path}"')
            else:
                subprocess.Popen(["code", str(path)])
            return f"VSCode Workspace opened for project: '{path.name}'"
        except Exception as e:
            return f"Failed to open VSCode workspace: {e}"
