import base64
import secrets
from typing import Optional, Dict

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class AESGCMEngine:
    """
    AES-256-GCM encryption engine.
    Provides authenticated encryption for files and in-memory data.
    """

    def __init__(self, master_key: bytes):
        if len(master_key) != 32:
            raise ValueError("AES-256 requires 32-byte key")

        self._aesgcm = AESGCM(master_key)

    @staticmethod
    def _generate_nonce() -> bytes:
        """
        Generate cryptographically secure 96-bit nonce.
        """
        return secrets.token_bytes(12)

    def encrypt(
        self,
        plaintext: bytes,
        associated_data: Optional[bytes] = None
    ) -> Dict[str, str]:
        """
        Encrypt bytes using AES-256-GCM.

        Returns a portable encryption package.
        """
        nonce = self._generate_nonce()

        ciphertext = self._aesgcm.encrypt(
            nonce=nonce,
            data=plaintext,
            associated_data=associated_data
        )

        return {
            "ciphertext": base64.b64encode(ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(nonce).decode("utf-8"),
            "algorithm": "AES-256-GCM",
            "version": 1
        }

    def decrypt(
        self,
        package: Dict[str, str],
        associated_data: Optional[bytes] = None
    ) -> bytes:
        """
        Decrypt AES-256-GCM encrypted package.

        Raises InvalidTag if tampered or wrong key.
        """
        nonce = base64.b64decode(package["nonce"])
        ciphertext = base64.b64decode(package["ciphertext"])

        return self._aesgcm.decrypt(
            nonce=nonce,
            data=ciphertext,
            associated_data=associated_data
        )
