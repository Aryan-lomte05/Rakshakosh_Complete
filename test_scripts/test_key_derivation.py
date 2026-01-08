from backend.security.key_derivation import (
    initialize_vault_metadata,
    load_vault_salt,
    derive_master_key
)

VAULT_DIR = "vault"

def main():
    # Initialize vault metadata on first run
    try:
        salt = initialize_vault_metadata(VAULT_DIR)
        print("Vault initialized")
    except RuntimeError:
        salt = load_vault_salt(VAULT_DIR)
        print("Vault already initialized")

    # Derive master key
    key = derive_master_key("MySecurePassword@2026!", salt)

    print("Derived key length:", len(key))
    print("Key fingerprint:", key.hex()[:16], "...")

if __name__ == "__main__":
    main()
