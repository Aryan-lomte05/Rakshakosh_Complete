"""
File Encryption/Decryption Service

Handles:
- Encrypting all files in protected folder (initial setup)
- Decrypting files in-place based on user's tier level on login
- Re-encrypting files on logout (optional)
"""

import os
import json
from typing import List, Tuple

from backend.rbac.tier_config import PROTECTED_FOLDER, can_access_file
from backend.security.aes_gcm import AESGCMEngine
from backend.security.document_crypto import DocumentCrypto

# =============================================================================
# CONFIGURATION
# =============================================================================

MASTER_KEY_PATH = "backend/security/master.key"


def _get_master_key() -> bytes:
    """Load or generate the master encryption key."""
    if os.path.exists(MASTER_KEY_PATH):
        with open(MASTER_KEY_PATH, "rb") as f:
            return f.read()
    else:
        key = os.urandom(32)
        os.makedirs(os.path.dirname(MASTER_KEY_PATH), exist_ok=True)
        with open(MASTER_KEY_PATH, "wb") as f:
            f.write(key)
        print(f"🔑 Generated new master key at {MASTER_KEY_PATH}")
        return key


def _get_crypto() -> DocumentCrypto:
    """Get document crypto instance."""
    key = _get_master_key()
    return DocumentCrypto(AESGCMEngine(key))


# =============================================================================
# ENCRYPT ALL FILES (Initial Setup)
# =============================================================================

def encrypt_all_files(folder: str = None) -> List[str]:
    """
    Encrypt all plain files in the folder.
    Creates .enc versions and removes originals.
    
    Returns list of encrypted files.
    """
    folder = folder or PROTECTED_FOLDER
    
    if not os.path.exists(folder):
        print(f"❌ Folder not found: {folder}")
        return []
    
    crypto = _get_crypto()
    encrypted = []
    
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        
        # Skip directories, hidden files, and already encrypted files
        if os.path.isdir(file_path) or filename.startswith('.') or filename.endswith('.enc'):
            continue
        
        # Encrypt the file
        enc_path = file_path + ".enc"
        try:
            # Read file
            with open(file_path, "rb") as f:
                plaintext = f.read()
            
            # Encrypt
            aes = AESGCMEngine(_get_master_key())
            encrypted_data = aes.encrypt(plaintext, associated_data=filename.encode("utf-8"))
            
            # Save encrypted
            with open(enc_path, "w", encoding="utf-8") as f:
                json.dump(encrypted_data, f)
            
            # Remove original
            os.remove(file_path)
            
            encrypted.append(filename)
            print(f"🔒 Encrypted: {filename} → {filename}.enc")
            
        except Exception as e:
            print(f"❌ Failed to encrypt {filename}: {e}")
    
    return encrypted


# =============================================================================
# DECRYPT FILES FOR USER'S TIER (On Login)
# =============================================================================

def decrypt_files_for_tier(tier_level: int, folder: str = None) -> Tuple[List[str], List[str]]:
    """
    Decrypt files in-place that the user's tier can access.
    
    Returns (decrypted_files, skipped_files)
    """
    folder = folder or PROTECTED_FOLDER
    
    if not os.path.exists(folder):
        print(f"❌ Folder not found: {folder}")
        return [], []
    
    decrypted = []
    skipped = []
    
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        
        # Only process .enc files
        if os.path.isdir(file_path) or not filename.endswith('.enc'):
            continue
        
        # Get original filename (without .enc)
        original_name = filename[:-4]
        
        # Check if user can access this file
        if not can_access_file(tier_level, original_name):
            skipped.append(original_name)
            continue
        
        # Decrypt the file
        try:
            # Read encrypted data
            with open(file_path, "r", encoding="utf-8") as f:
                encrypted_data = json.load(f)
            
            # Decrypt
            aes = AESGCMEngine(_get_master_key())
            plaintext = aes.decrypt(encrypted_data, associated_data=original_name.encode("utf-8"))
            
            # Save decrypted file
            original_path = os.path.join(folder, original_name)
            with open(original_path, "wb") as f:
                f.write(plaintext)
            
            decrypted.append(original_name)
            print(f"🔓 Decrypted: {original_name}")
            
        except Exception as e:
            print(f"❌ Failed to decrypt {filename}: {e}")
            skipped.append(original_name)
    
    return decrypted, skipped


# =============================================================================
# RE-ENCRYPT FILES (On Logout - Optional)
# =============================================================================

def reencrypt_all_decrypted(folder: str = None) -> List[str]:
    """
    Re-encrypt any decrypted files (cleanup on logout).
    Only encrypts files that have a corresponding .enc version.
    
    Returns list of re-encrypted files.
    """
    folder = folder or PROTECTED_FOLDER
    
    if not os.path.exists(folder):
        return []
    
    reencrypted = []
    
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)
        
        # Skip directories, hidden files, and .enc files
        if os.path.isdir(file_path) or filename.startswith('.') or filename.endswith('.enc'):
            continue
        
        # Check if .enc version exists (meaning this was decrypted)
        enc_path = file_path + ".enc"
        if os.path.exists(enc_path):
            # Just remove the decrypted version, .enc is still there
            os.remove(file_path)
            reencrypted.append(filename)
            print(f"🔒 Cleaned up: {filename}")
    
    return reencrypted


# =============================================================================
# CLI / TESTING
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("\n" + "="*60)
    print("📁 File Encryption Manager")
    print("="*60)
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python -m backend.documents.file_crypto encrypt   # Encrypt all files")
        print("  python -m backend.documents.file_crypto decrypt 2 # Decrypt for tier 2")
        print("  python -m backend.documents.file_crypto cleanup   # Re-encrypt all")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "encrypt":
        print("\n🔒 Encrypting all files...")
        encrypted = encrypt_all_files()
        print(f"\n✅ Encrypted {len(encrypted)} files")
        
    elif action == "decrypt":
        tier = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        print(f"\n🔓 Decrypting files for Tier {tier}...")
        decrypted, skipped = decrypt_files_for_tier(tier)
        print(f"\n✅ Decrypted: {len(decrypted)} files")
        print(f"⏭️ Skipped (no access): {len(skipped)} files")
        
    elif action == "cleanup":
        print("\n🔒 Re-encrypting all decrypted files...")
        reencrypted = reencrypt_all_decrypted()
        print(f"\n✅ Cleaned up {len(reencrypted)} files")
    
    else:
        print(f"❌ Unknown action: {action}")
