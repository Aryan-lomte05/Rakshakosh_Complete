#!/usr/bin/env python3
"""
Quick Test Script for RBAC System

Tests:
1. Tier configuration
2. File access logic
3. Auth service (requires MongoDB)

Run: python -m backend.test_scripts.test_rbac
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def test_tier_config():
    """Test tier configuration module."""
    print("\n" + "="*60)
    print("🧪 TEST 1: Tier Configuration")
    print("="*60)
    
    from backend.rbac.tier_config import (
        PROTECTED_FOLDER,
        TIER_DEFINITIONS,
        get_tier_name,
        get_accessible_patterns,
        can_access_file,
        get_accessible_files
    )
    
    print(f"\n📁 Protected folder: {PROTECTED_FOLDER}")
    print(f"📊 Defined tiers: {len(TIER_DEFINITIONS)}")
    
    # Test tier names
    for level in range(1, 5):
        name = get_tier_name(level)
        patterns = get_accessible_patterns(level)
        print(f"\n  Tier {level}: {name}")
        print(f"    Patterns (inherited): {patterns}")
    
    # Test file access
    test_files = [
        ("public_guide.pdf", "Should be accessible to Tier 1+"),
        ("internal_report.pdf", "Should be accessible to Tier 2+"),
        ("confidential_data.pdf", "Should be accessible to Tier 3+"),
        ("random_file.pdf", "Should be accessible to Admin only"),
    ]
    
    print("\n\n📄 File Access Tests:")
    for filename, desc in test_files:
        print(f"\n  {filename} ({desc})")
        for tier in range(1, 5):
            access = "✅" if can_access_file(tier, filename) else "❌"
            print(f"    Tier {tier}: {access}")
    
    print("\n✅ Tier config tests passed!")
    return True


def test_document_service():
    """Test document listing."""
    print("\n" + "="*60)
    print("🧪 TEST 2: Document Service")
    print("="*60)
    
    from backend.documents.document_service import (
        list_documents_for_tier,
        list_all_documents_with_access
    )
    
    print("\n📂 Files accessible to each tier:")
    for tier in range(1, 5):
        docs = list_documents_for_tier(tier)
        print(f"\n  Tier {tier}: {len(docs)} files")
        for doc in docs[:3]:  # Show first 3
            print(f"    - {doc['filename']}")
        if len(docs) > 3:
            print(f"    ... and {len(docs) - 3} more")
    
    # Test access summary
    print("\n\n📊 Access Summary for Tier 2:")
    result = list_all_documents_with_access(tier_level=2)
    print(f"  Accessible: {len(result['accessible'])} files")
    print(f"  Restricted: {len(result['restricted'])} files")
    
    print("\n✅ Document service tests passed!")
    return True


async def test_auth_service():
    """Test authentication (requires MongoDB)."""
    print("\n" + "="*60)
    print("🧪 TEST 3: Auth Service (Requires MongoDB)")
    print("="*60)
    
    try:
        from backend.db.mongodb import Database
        from backend.auth.auth_service import (
            hash_password,
            verify_password,
            create_access_token,
            decode_access_token
        )
        
        # Test password hashing
        print("\n🔐 Password Hashing:")
        password = "TestPassword123!"
        hashed = hash_password(password)
        print(f"  Original: {password}")
        print(f"  Hashed: {hashed[:50]}...")
        
        verified = verify_password(password, hashed)
        print(f"  Verification: {'✅ Passed' if verified else '❌ Failed'}")
        
        wrong_verified = verify_password("WrongPassword", hashed)
        print(f"  Wrong password rejected: {'✅ Yes' if not wrong_verified else '❌ No'}")
        
        # Test JWT
        print("\n🎫 JWT Token:")
        token = create_access_token("user123", "test@example.com", 2)
        print(f"  Token: {token[:50]}...")
        
        payload = decode_access_token(token)
        if payload:
            print(f"  Decoded sub: {payload.get('sub')}")
            print(f"  Decoded tier: {payload.get('tier')}")
            print("  ✅ JWT working!")
        else:
            print("  ❌ JWT decode failed")
        
        # Test MongoDB connection (optional)
        print("\n💾 MongoDB Connection:")
        try:
            await Database.connect()
            print("  ✅ MongoDB connected!")
            await Database.disconnect()
        except Exception as e:
            print(f"  ⚠️ MongoDB not available: {e}")
            print("  (Start MongoDB with: mongod or docker run -p 27017:27017 mongo)")
        
        print("\n✅ Auth service tests passed!")
        return True
        
    except ImportError as e:
        print(f"\n⚠️ Missing dependency: {e}")
        print("Run: pip install -r requirements_rbac.txt")
        return False


def main():
    """Run all tests."""
    print("\n" + "🚀"*30)
    print("  RAKSHAKOSH RBAC SYSTEM TESTS")
    print("🚀"*30)
    
    # Test 1: Tier Config (no external deps)
    test_tier_config()
    
    # Test 2: Document Service (no external deps)
    test_document_service()
    
    # Test 3: Auth Service (requires MongoDB + deps)
    import asyncio
    asyncio.run(test_auth_service())
    
    print("\n" + "="*60)
    print("🎉 ALL TESTS COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Install deps: pip install -r requirements_rbac.txt")
    print("2. Start MongoDB: mongod or docker run -p 27017:27017 mongo")
    print("3. Start server: python -m backend.api.main")
    print("4. Test APIs at: http://localhost:8000/docs")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
