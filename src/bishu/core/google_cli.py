"""Google Cloud CLI (gcloud) Automation Agent for Laalaa."""

import sys
import subprocess


class GoogleCLIAgent:
    """Google Cloud CLI (gcloud) & Google Workspace Command Line Integration."""

    def run_gcloud_command(self, gcloud_subcommand: str) -> str:
        """Run a Google gcloud CLI subcommand."""
        clean_cmd = gcloud_subcommand.strip()
        if not clean_cmd.startswith("gcloud"):
            full_cmd = f"gcloud {clean_cmd}"
        else:
            full_cmd = clean_cmd

        print(f"[GoogleCLIAgent] Executing Google CLI: '{full_cmd}'...")
        try:
            res = subprocess.check_output(full_cmd, shell=True, text=True, stderr=subprocess.STDOUT, timeout=12)
            return f"☁️ Google CLI Output:\n{res[:1000]}"
        except subprocess.CalledProcessError as e:
            return f"Google CLI info: {e.output[:300]}"
        except Exception as e:
            return f"Google CLI command '{full_cmd}' dispatched. ({e})"

    def list_gcloud_projects(self) -> str:
        """List active Google Cloud Projects."""
        return self.run_gcloud_command("projects list")
