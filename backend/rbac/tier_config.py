"""
RBAC Configuration - Tier-Based Access Control

This file defines:
1. PROTECTED_FOLDER - Where encrypted/accessible documents are stored
2. TIER_DEFINITIONS - Access levels and their file patterns
3. Helper functions for tier access checks

Edit TIER_DEFINITIONS to customize access levels.
"""

import os
import fnmatch
from typing import List, Dict

# =============================================================================
# CONFIGURATION - EDIT THESE AS NEEDED
# =============================================================================

# Folder containing documents for RBAC (relative to project root)
PROTECTED_FOLDER = "backend/test_docs"

# Tier definitions with inheritance
# Each tier can access files matching their patterns + all lower tier patterns
# 
# FILES IN test_docs: a.pdf, b.pdf, c.pdf, d.pdf, e.pdf, f.pdf
# 
TIER_DEFINITIONS: Dict[int, Dict] = {
    1: {
        "name": "Intern",
        "description": "Basic access - only a.pdf and b.pdf",
        "patterns": ["a.pdf", "b.pdf"],
    },
    2: {
        "name": "Analyst", 
        "description": "Standard access - adds c.pdf and d.pdf",
        "patterns": ["c.pdf", "d.pdf"],
    },
    3: {
        "name": "Manager",
        "description": "Elevated access - adds e.pdf",
        "patterns": ["e.pdf"],
    },
    4: {
        "name": "Admin",
        "description": "Full access - all documents including f.pdf",
        "patterns": ["*"],  # Wildcard = everything
    },
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_tier_name(tier_level: int) -> str:
    """Get human-readable tier name."""
    return TIER_DEFINITIONS.get(tier_level, {}).get("name", f"Tier {tier_level}")


def get_accessible_patterns(tier_level: int) -> List[str]:
    """
    Get all file patterns accessible to a tier level.
    Includes patterns from current tier + all lower tiers (inheritance).
    """
    patterns = []
    for level in range(1, tier_level + 1):
        tier_patterns = TIER_DEFINITIONS.get(level, {}).get("patterns", [])
        patterns.extend(tier_patterns)
    return list(set(patterns))  # Remove duplicates


def can_access_file(tier_level: int, filename: str) -> bool:
    """
    Check if a tier level can access a specific file.
    Admin (tier 4) can access everything.
    """
    if tier_level >= 4:  # Admin
        return True
    
    patterns = get_accessible_patterns(tier_level)
    filename_lower = filename.lower()
    
    for pattern in patterns:
        if fnmatch.fnmatch(filename_lower, pattern.lower()):
            return True
    
    return False


def get_accessible_files(tier_level: int, folder_path: str = None) -> List[str]:
    """
    Get list of files accessible to a tier level.
    Returns filenames that the user can access.
    """
    folder = folder_path or PROTECTED_FOLDER
    
    if not os.path.exists(folder):
        return []
    
    all_files = os.listdir(folder)
    accessible = []
    
    for filename in all_files:
        # Skip directories and hidden files
        file_path = os.path.join(folder, filename)
        if os.path.isdir(file_path) or filename.startswith('.'):
            continue
        
        if can_access_file(tier_level, filename):
            accessible.append(filename)
    
    return sorted(accessible)


def get_all_tiers() -> Dict[int, Dict]:
    """Return all tier definitions for display."""
    return TIER_DEFINITIONS


# =============================================================================
# FOR TESTING - Run this file directly
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("TIER DEFINITIONS")
    print("=" * 60)
    
    for level, info in TIER_DEFINITIONS.items():
        print(f"\nTier {level}: {info['name']}")
        print(f"  Patterns: {info['patterns']}")
        accessible = get_accessible_patterns(level)
        print(f"  Can access (inherited): {accessible}")
    
    print("\n" + "=" * 60)
    print("FILE ACCESS TEST")
    print("=" * 60)
    
    test_files = ["public_guide.pdf", "internal_report.pdf", "confidential_data.pdf", "random.pdf"]
    for tier in [1, 2, 3, 4]:
        print(f"\nTier {tier} ({get_tier_name(tier)}) can access:")
        for f in test_files:
            access = "✅" if can_access_file(tier, f) else "❌"
            print(f"  {access} {f}")
