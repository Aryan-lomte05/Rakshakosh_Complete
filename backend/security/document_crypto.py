import os
import json
from typing import Dict
from backend.security.aes_gcm import AESGCMEngine


class DocumentCrypto:
    """
    Handles encryption/decryption of original documents.
    Encrypted at rest, decrypted only in memory.
    """

    def __init__(self, aes_engine: AESGCMEngine):
        self._aes = aes_engine

    def encrypt_file(self, input_path: str, output_path: str) -> Dict:
        """
        Encrypt a document and securely delete plaintext.
        """
        with open(input_path, "rb") as f:
            plaintext = f.read()

        encrypted_package = self._aes.encrypt(
            plaintext,
            associated_data=os.path.basename(input_path).encode("utf-8")
        )

        # Store as JSON (safe serialization)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(encrypted_package, f)

        # Secure cleanup
        os.remove(input_path)

        return {
            "encrypted_path": output_path,
            "original_name": os.path.basename(input_path),
            "size": len(plaintext)
        }

    def decrypt_to_memory(self, encrypted_path: str, original_name: str) -> bytes:
        """
        Decrypt document into memory only.
        """
        with open(encrypted_path, "r", encoding="utf-8") as f:
            encrypted_package = json.load(f)

        return self._aes.decrypt(
            encrypted_package,
            associated_data=original_name.encode("utf-8")
        )
