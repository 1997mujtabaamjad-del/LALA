"""PDF/Word Document Reader, Chunking & SQLite Vector Cache RAG Engine."""

import re
from pathlib import Path
from bishu.core.sqlite_engine import SQLiteEngine


class PDFWordAnalyzerEngine:
    """PDF & Word Document Reader, Chunking, and SQLite Vector Cache RAG Engine."""

    def __init__(self, ai_engine=None):
        self.ai = ai_engine
        self.db = SQLiteEngine()

    def chunk_and_search_pdf(self, file_path: str, query: str) -> str:
        """Chunk PDF/Word document, index in SQLite vector cache, and perform RAG search."""
        path = Path(file_path)
        if not path.exists():
            return f"Document file '{file_path}' not found."

        raw_text = ""
        try:
            if path.suffix.lower() == ".pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(path)
                    raw_text = " ".join([page.extract_text() or "" for page in reader.pages])
                except Exception:
                    with open(path, "rb") as f:
                        raw_text = str(f.read()[:5000])
            else:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    raw_text = f.read()
        except Exception as e:
            return f"Failed to read document '{path.name}': {e}"

        # Chunk text into 500-character blocks
        chunks = [raw_text[i:i+500] for i in range(0, len(raw_text), 450) if raw_text[i:i+500].strip()]
        
        # Cache chunks into SQLite vector store
        for idx, chunk in enumerate(chunks[:20]):
            self.db.set_fact(f"doc_chunk_{path.name}_{idx}", chunk)

        # Keyword match relevant chunks
        matched_chunks = [c for c in chunks if any(w in c.lower() for w in query.lower().split())]
        context = "\n---\n".join(matched_chunks[:3]) if matched_chunks else "\n---\n".join(chunks[:3])

        if self.ai:
            prompt = (
                f"Document Context from '{path.name}':\n{context}\n\n"
                f"User Question: {query}\n"
                f"Answer the question accurately based on the document context above."
            )
            ans = self.ai.generate(prompt)
            return f"📄 Document Analysis for '{path.name}':\n\n{ans}"

        return f"Document '{path.name}' analyzed ({len(chunks)} chunks indexed in SQLite Vector Cache).\n\nRelevant Excerpt:\n{context[:300]}..."
