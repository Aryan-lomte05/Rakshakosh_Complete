import os
from backend.security.key_derivation import load_vault_salt, derive_master_key
from backend.security.aes_gcm import AESGCMEngine
from backend.security.document_crypto import DocumentCrypto

VAULT_DIR = "vault"
TEST_FILE = "secret_doc.txt"
ENC_FILE = "secret_doc.txt.enc"

# Create test file
with open(TEST_FILE, "w", encoding="utf-8") as f:
    f.write("CLASSIFIED PAYLOAD – DO NOT LEAK")


salt = load_vault_salt(VAULT_DIR)
key = derive_master_key("MySecurePassword@2026!", salt)

aes = AESGCMEngine(key)
doc_crypto = DocumentCrypto(aes)

meta = doc_crypto.encrypt_file(TEST_FILE, ENC_FILE)
print("Encrypted:", meta)

assert not os.path.exists(TEST_FILE)

data = doc_crypto.decrypt_to_memory(ENC_FILE, meta["original_name"])
print("Decrypted:", data.decode("utf-8", errors="replace"))

