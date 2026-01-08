from backend.security.key_derivation import load_vault_salt, derive_master_key
from backend.security.aes_gcm import AESGCMEngine

VAULT_DIR = "vault"

salt = load_vault_salt(VAULT_DIR)
key = derive_master_key("MySecurePassword@2026!", salt)

engine = AESGCMEngine(key)

data = b"Top secret classified payload"
aad = b"doc_id:classified_001"

encrypted = engine.encrypt(data, associated_data=aad)
print("Encrypted package:", encrypted)

decrypted = engine.decrypt(encrypted, associated_data=aad)
print("Decrypted:", decrypted.decode())
