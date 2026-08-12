"""Monitor engine for CPU and RAM system metrics."""

import psutil


class MonitorEngine:
    """System resource monitoring engine."""

    def __init__(self):
        self.cpu_history = []
        self.ram_history = []

    def sample(self) -> tuple:
        """Sample current CPU and RAM usage percentages."""
        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent

        self.cpu_history.append(cpu)
        self.ram_history.append(ram)

        return cpu, ram
