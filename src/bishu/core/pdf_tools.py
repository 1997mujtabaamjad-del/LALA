"""PDF Split & Merge Tools Engine."""

from pathlib import Path


class PDFSplitMergeEngine:
    """PDF Split and Merge Utility Tools."""

    def merge_pdfs(self, pdf_paths: list, output_filename: str = "Merged_Document.pdf") -> str:
        """Merge multiple PDF files into a single combined PDF."""
        out_dir = Path.home() / ".bishu" / "pdf_output"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / output_filename

        valid_paths = [Path(p) for p in pdf_paths if Path(p).exists()]
        if not valid_paths:
            return "No valid PDF file paths provided for merging."

        try:
            import pypdf
            merger = pypdf.PdfWriter()
            for p in valid_paths:
                merger.append(str(p))
            merger.write(str(out_file))
            merger.close()
            return f"📄 Merged {len(valid_paths)} PDF file(s) into: {out_file}"
        except Exception as e:
            return f"Failed to merge PDFs: {e}"

    def split_pdf(self, pdf_path: str) -> str:
        """Split a multi-page PDF into individual single-page PDFs."""
        path = Path(pdf_path)
        if not path.exists():
            return f"PDF file '{pdf_path}' not found."

        out_dir = Path.home() / ".bishu" / "pdf_output" / f"Split_{path.stem}"
        out_dir.mkdir(parents=True, exist_ok=True)

        try:
            import pypdf
            reader = pypdf.PdfReader(path)
            for i, page in enumerate(reader.pages, start=1):
                writer = pypdf.PdfWriter()
                writer.add_page(page)
                page_file = out_dir / f"Page_{i}.pdf"
                writer.write(str(page_file))
                writer.close()

            return f"📄 PDF '{path.name}' successfully split into {len(reader.pages)} individual page PDF(s) in: {out_dir.name}"
        except Exception as e:
            return f"Failed to split PDF: {e}"
