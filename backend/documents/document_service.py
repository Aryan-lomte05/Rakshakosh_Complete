"""
Document Service

Handles:
- Listing accessible documents for a user based on tier
- Decrypting documents for viewing
- Document metadata management
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from backend.rbac.tier_config import (
    PROTECTED_FOLDER,
    can_access_file,
    get_accessible_files,
    get_tier_name
)
from backend.security.aes_gcm import AESGCMEngine
from backend.security.document_crypto import DocumentCrypto


# =============================================================================
# CONFIGURATION
# =============================================================================

# Master key path (same as used in ingestion_api.py)
MASTER_KEY_PATH = "backend/security/master.key"


def _get_master_key() -> bytes:
    """Load or generate the master encryption key."""
    if os.path.exists(MASTER_KEY_PATH):
        with open(MASTER_KEY_PATH, "rb") as f:
            return f.read()
    else:
        # Generate new key if doesn't exist
        key = os.urandom(32)
        os.makedirs(os.path.dirname(MASTER_KEY_PATH), exist_ok=True)
        with open(MASTER_KEY_PATH, "wb") as f:
            f.write(key)
        return key


def _get_crypto() -> DocumentCrypto:
    """Get document crypto instance."""
    key = _get_master_key()
    return DocumentCrypto(AESGCMEngine(key))


# =============================================================================
# DOCUMENT LISTING
# =============================================================================

def list_documents_for_tier(tier_level: int) -> List[Dict[str, Any]]:
    """
    List all documents accessible to a given tier level.
    
    Returns list of document info dicts.
    """
    if not os.path.exists(PROTECTED_FOLDER):
        return []
    
    all_files = os.listdir(PROTECTED_FOLDER)
    documents = []
    
    for filename in sorted(all_files):
        file_path = os.path.join(PROTECTED_FOLDER, filename)
        
        # Skip directories and hidden files
        if os.path.isdir(file_path) or filename.startswith('.'):
            continue
        
        # Check if user can access this file
        # For encrypted files, check the base name (without .enc)
        check_name = filename[:-4] if filename.endswith('.enc') else filename
        
        if not can_access_file(tier_level, check_name):
            continue
        
        # Get file info
        stat = os.stat(file_path)
        is_encrypted = filename.endswith('.enc')
        
        documents.append({
            "filename": filename,
            "display_name": filename[:-4] if is_encrypted else filename,
            "size_bytes": stat.st_size,
            "size_readable": _format_size(stat.st_size),
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "is_encrypted": is_encrypted,
            "accessible": True
        })
    
    return documents


def list_all_documents_with_access(tier_level: int) -> Dict[str, List[Dict]]:
    """
    List ALL documents, marking which ones are accessible.
    
    Good for showing users what they can and cannot access.
    """
    if not os.path.exists(PROTECTED_FOLDER):
        return {"accessible": [], "restricted": []}
    
    all_files = os.listdir(PROTECTED_FOLDER)
    accessible = []
    restricted = []
    
    for filename in sorted(all_files):
        file_path = os.path.join(PROTECTED_FOLDER, filename)
        
        if os.path.isdir(file_path) or filename.startswith('.'):
            continue
        
        check_name = filename[:-4] if filename.endswith('.enc') else filename
        can_access = can_access_file(tier_level, check_name)
        
        stat = os.stat(file_path)
        is_encrypted = filename.endswith('.enc')
        
        doc_info = {
            "filename": filename,
            "display_name": filename[:-4] if is_encrypted else filename,
            "size_bytes": stat.st_size,
            "size_readable": _format_size(stat.st_size),
            "is_encrypted": is_encrypted
        }
        
        if can_access:
            accessible.append(doc_info)
        else:
            restricted.append(doc_info)
    
    return {"accessible": accessible, "restricted": restricted}


# =============================================================================
# DOCUMENT DECRYPTION
# =============================================================================

def decrypt_document(filename: str, tier_level: int) -> Optional[bytes]:
    """
    Decrypt a document if user has access.
    
    Returns decrypted bytes or None if access denied or file not found.
    """
    # Check access
    check_name = filename[:-4] if filename.endswith('.enc') else filename
    if not can_access_file(tier_level, check_name):
        return None
    
    file_path = os.path.join(PROTECTED_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return None
    
    # If not encrypted, just read the file
    if not filename.endswith('.enc'):
        with open(file_path, "rb") as f:
            return f.read()
    
    # Decrypt encrypted file
    try:
        crypto = _get_crypto()
        # Get original name (without .enc)
        original_name = filename[:-4]
        decrypted = crypto.decrypt_to_memory(file_path, original_name)
        return decrypted
    except Exception as e:
        print(f"❌ Decryption failed for {filename}: {e}")
        return None


def get_document_info(filename: str, tier_level: int) -> Optional[Dict[str, Any]]:
    """
    Get detailed info about a specific document.
    """
    file_path = os.path.join(PROTECTED_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return None
    
    check_name = filename[:-4] if filename.endswith('.enc') else filename
    can_access = can_access_file(tier_level, check_name)
    
    stat = os.stat(file_path)
    is_encrypted = filename.endswith('.enc')
    
    return {
        "filename": filename,
        "display_name": filename[:-4] if is_encrypted else filename,
        "size_bytes": stat.st_size,
        "size_readable": _format_size(stat.st_size),
        "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        "is_encrypted": is_encrypted,
        "accessible": can_access,
        "requires_tier": _get_required_tier(check_name) if not can_access else tier_level
    }


# =============================================================================
# HELPERS
# =============================================================================

def _format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _get_required_tier(filename: str) -> int:
    """Determine the minimum tier required to access a file."""
    for tier in [1, 2, 3, 4]:
        if can_access_file(tier, filename):
            return tier
    return 4  # Default to admin if no match
