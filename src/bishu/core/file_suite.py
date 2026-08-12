"""File Explorer Suite for duplicate file scanning, folder auto-organization, batch renamer, file search, and ZIP archive control."""

import os
import shutil
import zipfile
import hashlib
from pathlib import Path


class FileExplorerSuiteEngine:
    """File Explorer Suite for duplicate scanning, auto-organizing, batch renaming, file search, and ZIP archives."""

    def scan_duplicate_files(self, folder_path: str) -> str:
        """Scan folder for duplicate files using MD5 hash matching."""
        target_dir = Path(folder_path)
        if not target_dir.exists():
            return f"Folder '{folder_path}' not found."

        hashes = {}
        duplicates = []

        for p in target_dir.rglob("*"):
            if p.is_file():
                try:
                    with open(p, "rb") as f:
                        file_hash = hashlib.md5(f.read()).hexdigest()
                    if file_hash in hashes:
                        duplicates.append((p.name, hashes[file_hash].name))
                    else:
                        hashes[file_hash] = p
                except Exception:
                    pass

        if duplicates:
            dup_str = "\n".join([f"- '{d[0]}' is duplicate of '{d[1]}'" for d in duplicates[:10]])
            return f"📁 Found {len(duplicates)} duplicate file(s) in '{target_dir.name}':\n{dup_str}"

        return f"📁 Duplicate File Scanner: 0 duplicates found in '{target_dir.name}'."

    def auto_organize_folder(self, folder_path: str) -> str:
        """Auto-organize folder files into categories (Documents, Images, Videos, Archives, Code)."""
        target_dir = Path(folder_path)
        if not target_dir.exists():
            return f"Folder '{folder_path}' not found."

        cat_map = {
            "Images": [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"],
            "Documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx", ".md"],
            "Videos": [".mp4", ".mkv", ".avi", ".mov"],
            "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"],
            "Code": [".py", ".js", ".html", ".css", ".json", ".cpp", ".java"]
        }

        count = 0
        for item in target_dir.glob("*"):
            if item.is_file():
                ext = item.suffix.lower()
                moved = False
                for cat, exts in cat_map.items():
                    if ext in exts:
                        dest_dir = target_dir / cat
                        dest_dir.mkdir(exist_ok=True)
                        shutil.move(str(item), str(dest_dir / item.name))
                        count += 1
                        moved = True
                        break

        return f"📂 Auto-organized {count} file(s) into category subfolders in '{target_dir.name}'."

    def batch_rename_files(self, folder_path: str, prefix: str) -> str:
        """Batch rename files in folder sequentially (e.g. prefix_1.ext, prefix_2.ext)."""
        target_dir = Path(folder_path)
        if not target_dir.exists():
            return f"Folder '{folder_path}' not found."

        count = 0
        files = sorted([p for p in target_dir.glob("*") if p.is_file()])
        for idx, f in enumerate(files, start=1):
            new_name = f"{prefix}_{idx}{f.suffix}"
            f.rename(target_dir / new_name)
            count += 1

        return f"Batch renamed {count} file(s) in '{target_dir.name}' using prefix '{prefix}'."

    def search_files_on_pc(self, query: str, ext_filter: str = None) -> str:
        """Locate any file on PC with optional file extension filter."""
        search_root = Path.home()
        matches = []
        q = query.lower().strip()

        for p in search_root.rglob("*"):
            if p.is_file() and q in p.name.lower():
                if ext_filter and not p.suffix.lower().endswith(ext_filter.lower()):
                    continue
                matches.append(str(p))
                if len(matches) >= 10:
                    break

        if matches:
            res_str = "\n".join([f"- {m}" for m in matches])
            return f"🔍 File Search Results for '{query}':\n{res_str}"

        return f"No files found matching '{query}'."

    def compress_folder(self, folder_path: str) -> str:
        """Compress folder into ZIP archive."""
        target_dir = Path(folder_path)
        if not target_dir.exists():
            return f"Folder '{folder_path}' not found."

        zip_path = target_dir.with_suffix(".zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(target_dir):
                for f in files:
                    full_p = Path(root) / f
                    zipf.write(full_p, full_p.relative_to(target_dir))

        return f"📦 Folder '{target_dir.name}' compressed into ZIP archive: {zip_path.name}"

    def extract_zip(self, zip_path: str) -> str:
        """Extract ZIP archive contents."""
        path = Path(zip_path)
        if not path.exists():
            return f"ZIP file '{zip_path}' not found."

        dest_dir = path.with_suffix("")
        dest_dir.mkdir(exist_ok=True)
        with zipfile.ZipFile(path, "r") as zipf:
            zipf.extractall(dest_dir)

        return f"📦 ZIP archive '{path.name}' extracted to: {dest_dir.name}"

    def inspect_zip(self, zip_path: str) -> str:
        """Inspect contents of a ZIP archive."""
        path = Path(zip_path)
        if not path.exists():
            return f"ZIP file '{zip_path}' not found."

        with zipfile.ZipFile(path, "r") as zipf:
            contents = zipf.namelist()

        summary = "\n".join([f"- {c}" for c in contents[:10]])
        return f"📦 ZIP Contents ({len(contents)} files):\n{summary}"
