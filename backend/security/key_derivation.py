import os
import json
import secrets
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

VAULT_META_FILENAME = "vault_meta.json"
PBKDF2_ITERATIONS = 100_000
KEY_LENGTH = 32  # 256-bit


def initialize_vault_metadata(vault_dir: str) -> bytes:
    """
    First-run ONLY.
    Creates vault directory and salt metadata.
    """
    os.makedirs(vault_dir, exist_ok=True)
    meta_path = os.path.join(vault_dir, VAULT_META_FILENAME)

    if os.path.exists(meta_path):
        raise RuntimeError("Vault metadata already exists")

    salt = secrets.token_bytes(16)

    metadata = {
        "version": 1,
        "kdf": "PBKDF2-HMAC-SHA256",
        "iterations": PBKDF2_ITERATIONS,
        "salt": salt.hex()
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return salt


def load_vault_salt(vault_dir: str) -> bytes:
    """
    Load existing salt from vault metadata.
    """
    meta_path = os.path.join(vault_dir, VAULT_META_FILENAME)

    if not os.path.exists(meta_path):
        raise RuntimeError("Vault metadata not found")

    with open(meta_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return bytes.fromhex(metadata["salt"])


def derive_master_key(password: str, salt: bytes) -> bytes:
    """
    Derive AES-256 master key from password.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_LENGTH,
        salt=salt,
        iterations=PBKDF2_ITERATIONS,
        backend=default_backend()
    )

    return kdf.derive(password.encode("utf-8"))
