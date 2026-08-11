"""Graphify Knowledge Graph Engine for J.A.R.V.I.S. memory & neural node relationships."""

import json
from pathlib import Path

try:
    import networkx as nx
    HAS_NX = True
except Exception:
    nx = None
    HAS_NX = False


class GraphifyEngine:
    """Knowledge Graph Memory Engine for Laalaa."""

    def __init__(self, filepath=None):
        if filepath is None:
            filepath = Path.home() / ".bishu" / "knowledge_graph.json"
        self.filepath = Path(filepath)
        self.nodes_data = {}
        self.edges_data = []
        self._init_default_graph()

    def _init_default_graph(self):
        """Initialize core J.A.R.V.I.S. knowledge graph nodes."""
        default_nodes = [
            ("Laalaa", "Core AI Companion"),
            ("User", "Master/Boss"),
            ("YouTube", "Media Application"),
            ("Notepad", "System Application"),
            ("VSCode", "IDE Developer Tool"),
            ("YOLO Vision", "Computer Vision AI"),
            ("Whisper", "Speech Recognition STT"),
            ("Perplexity", "Live Web Search"),
        ]
        for name, category in default_nodes:
            self.add_node(name, category)

        default_edges = [
            ("Laalaa", "User", "Serves"),
            ("Laalaa", "YouTube", "Launches"),
            ("Laalaa", "Notepad", "Launches"),
            ("Laalaa", "VSCode", "Launches"),
            ("Laalaa", "YOLO Vision", "Executes"),
            ("Laalaa", "Whisper", "Transcribes"),
            ("Laalaa", "Perplexity", "Queries"),
        ]
        for src, tgt, rel in default_edges:
            self.add_edge(src, tgt, rel)

    def add_node(self, name: str, category: str = "General"):
        self.nodes_data[name] = category

    def add_edge(self, source: str, target: str, relationship: str = "Connected"):
        self.edges_data.append((source, target, relationship))

    def query_related(self, entity: str) -> list:
        """Query all connected entities in the Graphify Knowledge Network."""
        related = []
        for src, tgt, rel in self.edges_data:
            if src.lower() == entity.lower():
                related.append(f"{tgt} ({rel})")
            elif tgt.lower() == entity.lower():
                related.append(f"{src} ({rel})")
        return related

    def get_summary(self) -> str:
        return f"Graphify Knowledge Network active with {len(self.nodes_data)} nodes and {len(self.edges_data)} relationships."
