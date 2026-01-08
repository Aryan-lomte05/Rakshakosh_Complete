import json
import os
import base64
from datetime import datetime
from typing import Dict

from backend.security.aes_gcm import AESGCMEngine


class PasswordVault:
    """
    Encrypted vault for storing document passwords.
    Zero-knowledge, tamper-evident, offline-safe.
    """

    VAULT_FILENAME = "password_vault.enc"
    AAD = b"rakshakosh-password-vault"

    def __init__(self, aes_engine: AESGCMEngine, vault_dir: str):
        self._aes = aes_engine
        self._vault_dir = vault_dir
        self._vault_path = os.path.join(vault_dir, self.VAULT_FILENAME)
        self._data: Dict[str, dict] = {}

    # ----------------------------
    # Core operations
    # ----------------------------

    def store_password(self, doc_id: str, password: str, metadata: dict = None):
        """
        Store a document password (encrypted).
        """
        encrypted = self._aes.encrypt(
            password.encode("utf-8"),
            associated_data=doc_id.encode("utf-8")
        )

        self._data[doc_id] = {
            "doc_id": doc_id,
            "encrypted": encrypted,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat()
        }

    def retrieve_password(self, doc_id: str) -> str:
        """
        Decrypt and return document password.
        """
        entry = self._data[doc_id]

        plaintext = self._aes.decrypt(
            entry["encrypted"],
            associated_data=doc_id.encode("utf-8")
        )

        return plaintext.decode("utf-8")

    def verify_password(self, doc_id: str, user_password: str) -> bool:
        """
        Verify user-entered password.
        """
        try:
            return self.retrieve_password(doc_id) == user_password
        except Exception:
            return False

    # ----------------------------
    # Persistence
    # ----------------------------

    def save(self):
        """
        Encrypt and save entire vault to disk.
        """
        os.makedirs(self._vault_dir, exist_ok=True)

        vault_json = json.dumps(self._data, indent=2).encode("utf-8")

        encrypted = self._aes.encrypt(
            vault_json,
            associated_data=self.AAD
        )

        with open(self._vault_path, "wb") as f:
            f.write(json.dumps(encrypted).encode("utf-8"))

    def load(self):
        """
        Load and decrypt vault from disk.
        """
        if not os.path.exists(self._vault_path):
            return

        with open(self._vault_path, "rb") as f:
            encrypted = json.loads(f.read().decode("utf-8"))

        plaintext = self._aes.decrypt(
            encrypted,
            associated_data=self.AAD
        )

        self._data = json.loads(plaintext.decode("utf-8"))

    # ----------------------------
    # Utilities
    # ----------------------------

    def list_documents(self):
        """
        List documents without exposing passwords.
        """
        return [
            {
                "doc_id": doc_id,
                "metadata": entry["metadata"],
                "created_at": entry["created_at"]
            }
            for doc_id, entry in self._data.items()
        ]
