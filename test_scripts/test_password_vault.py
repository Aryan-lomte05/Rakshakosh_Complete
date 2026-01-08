from backend.security.key_derivation import load_vault_salt, derive_master_key
from backend.security.aes_gcm import AESGCMEngine
from backend.security.password_vault import PasswordVault

VAULT_DIR = "vault"

salt = load_vault_salt(VAULT_DIR)
key = derive_master_key("MySecurePassword@2026!", salt)

aes = AESGCMEngine(key)
vault = PasswordVault(aes, VAULT_DIR)

# Store passwords
vault.store_password(
    doc_id="classified_doc_001",
    password="TopSecretd@2025",
    metadata={"filename": "classified.pdf"}
)

vault.save()
print("Vault saved")

# Reload vault
vault2 = PasswordVault(aes, VAULT_DIR)
vault2.load()

print("Documents:", vault2.list_documents())
print("Password verified:",
      vault2.verify_password("classified_doc_001", "TopSecret@2025"))
