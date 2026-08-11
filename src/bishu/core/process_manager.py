"""Process & RAM Monitor Agent for listing active processes, CPU diagnostics, and terminating apps."""

import os

try:
    import psutil
    HAS_PSUTIL = True
except Exception:
    psutil = None
    HAS_PSUTIL = False


class ProcessManagerAgent:
    """Process & RAM Monitor Agent for process listing, CPU diagnostics, and app termination."""

    def list_active_processes(self, limit: int = 10) -> str:
        """List top CPU & RAM consuming active processes."""
        if not HAS_PSUTIL or not psutil:
            return "psutil package not available for process management."

        proc_list = []
        try:
            for p in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    p_info = p.info
                    proc_list.append(p_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            # Sort by memory percent
            proc_list.sort(key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)
            top_procs = proc_list[:limit]

            summary = [f"⚙️ Active Processes (Top {limit}):"]
            for p in top_procs:
                p_name = p.get('name')
                p_ram = p.get('memory_percent', 0) or 0
                summary.append(f"- {p_name} (PID {p.get('pid')}): RAM {p_ram:.1f}%")

            return "\n".join(summary)
        except Exception as e:
            return f"Failed to list active processes: {e}"

    def run_cpu_diagnostics(self) -> str:
        """Run CPU diagnostics (core counts, clock frequency, per-CPU load)."""
        if not HAS_PSUTIL or not psutil:
            return "psutil package not available for CPU diagnostics."

        try:
            phys_cores = psutil.cpu_count(logical=False)
            log_cores = psutil.cpu_count(logical=True)
            cpu_percent = psutil.cpu_percent(interval=0.2)
            per_cpu = psutil.per_cpu_percent(interval=0.2)
            ram = psutil.virtual_memory()

            return (
                f"💻 CPU & RAM Diagnostics Report:\n"
                f"- Physical Cores: {phys_cores} | Threads: {log_cores}\n"
                f"- Total CPU Utilization: {cpu_percent:.1f}%\n"
                f"- Per-Core Load: {per_cpu[:4]}...\n"
                f"- RAM Memory: {ram.percent}% used ({ram.used / (1024**3):.1f} GB / {ram.total / (1024**3):.1f} GB)"
            )
        except Exception as e:
            return f"CPU diagnostics error: {e}"

    def terminate_app(self, app_name: str) -> str:
        """Terminate active background application by process name."""
        if not HAS_PSUTIL or not psutil:
            return "psutil package not available to terminate app."

        clean_name = app_name.lower().strip()
        count = 0
        try:
            for p in psutil.process_iter(['pid', 'name']):
                try:
                    p_name = p.info.get('name', '').lower()
                    if clean_name in p_name:
                        p.kill()
                        count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            if count > 0:
                return f"Successfully terminated {count} process instance(s) matching '{app_name}'."
            return f"No active process found matching '{app_name}'."
        except Exception as e:
            return f"Failed to terminate app '{app_name}': {e}"
