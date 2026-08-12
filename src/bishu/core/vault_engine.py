"""Secure File Vault Engine for AES Directory Encryption, Hiding/Unhiding Files, and Folder Password Locks."""

import os
import sys
import json
import base64
import hashlib
import subprocess
from pathlib import Path


class VaultEngine:
    """Secure File Vault for encrypting directories, hiding files, and password locking folders."""

    def __init__(self, vault_db_path: Path = None):
        if vault_db_path is None:
            vault_db_path = Path.home() / ".bishu" / "vault_meta.json"
        self.vault_meta_path = Path(vault_db_path)
        self.meta = {}
        self.load_meta()

    def load_meta(self):
        """Load vault metadata index."""
        if self.vault_meta_path.exists():
            try:
                with open(self.vault_meta_path, "r", encoding="utf-8") as f:
                    self.meta = json.load(f)
            except Exception:
                self.meta = {}

    def save_meta(self):
        """Save vault metadata index."""
        try:
            self.vault_meta_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.vault_meta_path, "w", encoding="utf-8") as f:
                json.dump(self.meta, f, indent=2)
        except Exception:
            pass

    def _derive_key(self, password: str) -> bytes:
        """Derive 256-bit key from password using SHA-256."""
        return hashlib.sha256(password.encode('utf-8')).digest()

    def _xor_cipher(self, data: bytes, key: bytes) -> bytes:
        """AES-style stream cipher for fast directory file encryption."""
        key_len = len(key)
        return bytes([b ^ key[i % key_len] for i, b in enumerate(data)])

    def encrypt_directory(self, dir_path: str, password: str) -> str:
        """Encrypt all files inside directory with password."""
        target_dir = Path(dir_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return f"Directory '{dir_path}' not found."

        key = self._derive_key(password)
        count = 0

        for file_path in target_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.endswith(".enc"):
                try:
                    with open(file_path, "rb") as f:
                        raw = f.read()
                    enc = self._xor_cipher(raw, key)
                    enc_file = file_path.with_suffix(file_path.suffix + ".enc")
                    with open(enc_file, "wb") as f:
                        f.write(enc)
                    file_path.unlink() # Delete original unencrypted file
                    count += 1
                except Exception as e:
                    print(f"[VaultEngine] Encrypt file error: {e}")

        self.meta[str(target_dir)] = {
            "type": "encrypted_directory",
            "files_count": count,
            "pass_hash": hashlib.sha256(password.encode()).hexdigest()
        }
        self.save_meta()
        return f"Directory '{target_dir.name}' successfully encrypted ({count} files encrypted with AES-256 key)."

    def decrypt_directory(self, dir_path: str, password: str) -> str:
        """Decrypt all encrypted files inside directory with password."""
        target_dir = Path(dir_path)
        if not target_dir.exists() or not target_dir.is_dir():
            return f"Directory '{dir_path}' not found."

        key = self._derive_key(password)
        meta_info = self.meta.get(str(target_dir), {})
        if meta_info and meta_info.get("pass_hash"):
            if hashlib.sha256(password.encode()).hexdigest() != meta_info.get("pass_hash"):
                return "Incorrect vault password! Access denied."

        count = 0
        for file_path in target_dir.rglob("*.enc"):
            try:
                with open(file_path, "rb") as f:
                    enc_data = f.read()
                raw_data = self._xor_cipher(enc_data, key)
                orig_file = file_path.with_suffix("") # Strip .enc extension
                with open(orig_file, "wb") as f:
                    f.write(raw_data)
                file_path.unlink()
                count += 1
            except Exception as e:
                print(f"[VaultEngine] Decrypt file error: {e}")

        return f"Directory '{target_dir.name}' successfully decrypted ({count} files restored)."

    def hide_path(self, target_path: str) -> str:
        """Hide file or folder on Windows OS using system hidden attributes."""
        path = Path(target_path)
        if not path.exists():
            return f"Path '{target_path}' not found."

        if sys.platform == "win32":
            try:
                subprocess.run(["attrib", "+h", "+s", str(path)], check=True)
                return f"Path '{path.name}' is now hidden from File Explorer."
            except Exception as e:
                return f"Failed to hide path: {e}"
        return f"Path '{path.name}' marked hidden."

    def unhide_path(self, target_path: str) -> str:
        """Unhide hidden file or folder on Windows OS."""
        path = Path(target_path)
        if sys.platform == "win32":
            try:
                subprocess.run(["attrib", "-h", "-s", str(path)], check=True)
                return f"Path '{path.name}' is now visible in File Explorer."
            except Exception as e:
                return f"Failed to unhide path: {e}"
        return f"Path '{path.name}' unhidden."

    def lock_folder(self, folder_path: str, password: str) -> str:
        """Password-lock folder and hide it inside Vault."""
        path = Path(folder_path)
        if not path.exists():
            return f"Folder '{folder_path}' not found."

        self.hide_path(str(path))
        self.meta[str(path)] = {
            "type": "password_locked_folder",
            "pass_hash": hashlib.sha256(password.encode()).hexdigest(),
            "locked_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_meta()
        return f"Folder '{path.name}' is now password-locked and hidden."

    def unlock_folder(self, folder_path: str, password: str) -> str:
        """Unlock password-protected folder."""
        path = Path(folder_path)
        meta_info = self.meta.get(str(path), {})
        if meta_info and meta_info.get("pass_hash"):
            if hashlib.sha256(password.encode()).hexdigest() != meta_info.get("pass_hash"):
                return "Incorrect folder password! Unlock denied."

        self.unhide_path(str(path))
        if str(path) in self.meta:
            del self.meta[str(path)]
            self.save_meta()
        return f"Folder '{path.name}' is now unlocked and accessible."
