"""
Authentication Service

Handles:
- User signup with password hashing
- User login with JWT generation
- Password verification
- User key management with PasswordVault
"""

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from passlib.context import CryptContext
import jwt
from bson import ObjectId

from backend.db.mongodb import get_users_collection
from backend.rbac.tier_config import get_tier_name
from backend.auth.models import UserInDB, UserResponse

# =============================================================================
# CONFIGURATION
# =============================================================================

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "rakshakosh-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))

# Password hashing (Argon2 preferred, bcrypt fallback)
pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")


# =============================================================================
# PASSWORD FUNCTIONS
# =============================================================================

def hash_password(password: str) -> str:
    """Hash a password using Argon2."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================================
# JWT FUNCTIONS
# =============================================================================

def create_access_token(user_id: str, email: str, tier_level: int) -> str:
    """Create a JWT access token."""
    payload = {
        "sub": user_id,
        "email": email,
        "tier": tier_level,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# =============================================================================
# USER SERVICE FUNCTIONS
# =============================================================================

async def create_user(
    email: str, 
    password: str, 
    tier_level: int = 1,
    department: str = None
) -> Dict[str, Any]:
    """
    Create a new user.
    
    Returns dict with user data or raises exception on error.
    """
    users = get_users_collection()
    
    # Check if user exists
    existing = await users.find_one({"email": email.lower()})
    if existing:
        raise ValueError("User with this email already exists")
    
    # Hash password
    password_hash = hash_password(password)
    
    # Generate encryption key ID (will be used to store key in vault)
    encryption_key_id = f"user_key_{secrets.token_hex(8)}"
    
    # Create user document
    user_doc = {
        "email": email.lower(),
        "password_hash": password_hash,
        "tier_level": tier_level,
        "department": department,
        "encryption_key_id": encryption_key_id,
        "created_at": datetime.utcnow(),
        "last_login": None
    }
    
    # Insert into MongoDB
    result = await users.insert_one(user_doc)
    
    return {
        "id": str(result.inserted_id),
        "email": email.lower(),
        "tier_level": tier_level,
        "tier_name": get_tier_name(tier_level),
        "department": department,
        "encryption_key_id": encryption_key_id,
        "created_at": user_doc["created_at"]
    }


async def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by email and password.
    
    Returns user data if valid, None otherwise.
    """
    users = get_users_collection()
    
    # Find user
    user = await users.find_one({"email": email.lower()})
    if not user:
        return None
    
    # Verify password
    if not verify_password(password, user["password_hash"]):
        return None
    
    # Update last login
    await users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.utcnow()}}
    )
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "tier_level": user["tier_level"],
        "tier_name": get_tier_name(user["tier_level"]),
        "department": user.get("department"),
        "encryption_key_id": user.get("encryption_key_id"),
        "created_at": user["created_at"]
    }


async def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user by MongoDB ObjectId."""
    users = get_users_collection()
    
    try:
        user = await users.find_one({"_id": ObjectId(user_id)})
    except:
        return None
    
    if not user:
        return None
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "tier_level": user["tier_level"],
        "tier_name": get_tier_name(user["tier_level"]),
        "department": user.get("department"),
        "encryption_key_id": user.get("encryption_key_id"),
        "created_at": user["created_at"]
    }


async def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email address."""
    users = get_users_collection()
    
    user = await users.find_one({"email": email.lower()})
    if not user:
        return None
    
    return {
        "id": str(user["_id"]),
        "email": user["email"],
        "tier_level": user["tier_level"],
        "tier_name": get_tier_name(user["tier_level"]),
        "department": user.get("department"),
        "encryption_key_id": user.get("encryption_key_id"),
        "created_at": user["created_at"]
    }
