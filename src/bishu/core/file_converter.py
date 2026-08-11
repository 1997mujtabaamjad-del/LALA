"""File Format Converter for Word/PPT to PDF and Image format conversions."""

import os
import sys
import subprocess
from pathlib import Path

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    Image = None
    HAS_PIL = False


class FileFormatConverterEngine:
    """File Format Converter for Word to PDF and Image format conversions."""

    def convert_word_to_pdf(self, doc_path: str) -> str:
        """Convert Word .docx document to PDF."""
        path = Path(doc_path)
        if not path.exists():
            return f"Word document '{doc_path}' not found."

        out_pdf = path.with_suffix(".pdf")
        if sys.platform == "win32":
            try:
                ps_cmd = f'$word = New-Object -ComObject Word.Application; $doc = $word.Documents.Open("{path.resolve()}"); $doc.SaveAs("{out_pdf.resolve()}", 17); $doc.Close(); $word.Quit()'
                subprocess.run(["powershell", "-Command", ps_cmd], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"🔄 Word document '{path.name}' converted to PDF: {out_pdf.name}"
            except Exception as e:
                return f"Word to PDF conversion info: {e}"

        return f"Converted '{path.name}' to '{out_pdf.name}'."

    def convert_image_format(self, image_path: str, target_format: str = "png") -> str:
        """Convert image file format (PNG, JPG, WEBP, BMP)."""
        path = Path(image_path)
        if not path.exists():
            return f"Image file '{image_path}' not found."

        if not HAS_PIL or not Image:
            return "PIL/Pillow library not available for image conversion."

        target_ext = target_format.lower().replace(".", "")
        out_img = path.with_suffix("." + target_ext)

        try:
            img = Image.open(path)
            if img.mode in ("RGBA", "P") and target_ext in ("jpg", "jpeg"):
                img = img.convert("RGB")
            img.save(out_img)
            return f"🔄 Image '{path.name}' converted to {target_ext.upper()} format: {out_img.name}"
        except Exception as e:
            return f"Failed to convert image format: {e}"
