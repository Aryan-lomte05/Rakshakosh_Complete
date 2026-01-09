"""
Authentication API Endpoints

Provides:
- POST /auth/signup - Register new user
- POST /auth/login - Login and get JWT token (+ decrypt files for tier)
- POST /auth/logout - Logout and re-encrypt files
- GET /auth/me - Get current user profile
- GET /auth/tiers - Get all tier definitions
"""

from fastapi import APIRouter, HTTPException, Depends, status
from datetime import datetime

from backend.auth.models import (
    UserSignupRequest, 
    UserLoginRequest, 
    UserResponse, 
    TokenResponse,
    SignupResponse
)
from backend.auth.auth_service import (
    create_user,
    authenticate_user,
    create_access_token
)
from backend.auth.middleware import get_current_user
from backend.rbac.tier_config import get_tier_name, get_all_tiers, PROTECTED_FOLDER

# Import file crypto for in-place decryption
from backend.documents.file_crypto import decrypt_files_for_tier, reencrypt_all_decrypted

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: UserSignupRequest):
    """
    Register a new user.
    
    - **email**: Valid email address
    - **password**: Minimum 8 characters
    - **tier_level**: Access tier 1-4 (default: 1)
    - **department**: Optional department name
    """
    try:
        user_data = await create_user(
            email=request.email,
            password=request.password,
            tier_level=request.tier_level,
            department=request.department
        )
        
        return SignupResponse(
            message="User created successfully",
            user=UserResponse(
                id=user_data["id"],
                email=user_data["email"],
                tier_level=user_data["tier_level"],
                tier_name=user_data["tier_name"],
                department=user_data.get("department"),
                created_at=user_data["created_at"]
            )
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@router.post("/login")
async def login(request: UserLoginRequest):
    """
    Login and receive a JWT access token.
    
    **ALSO decrypts tier-accessible files in the protected folder!**
    
    - **email**: Registered email address
    - **password**: Account password
    
    Returns access token + list of decrypted files.
    """
    user_data = await authenticate_user(
        email=request.email,
        password=request.password
    )
    
    if not user_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Create JWT token
    access_token = create_access_token(
        user_id=user_data["id"],
        email=user_data["email"],
        tier_level=user_data["tier_level"]
    )
    
    # 🔓 DECRYPT FILES FOR THIS USER'S TIER
    tier_level = user_data["tier_level"]
    decrypted_files, restricted_files = decrypt_files_for_tier(tier_level)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user_data["id"],
            "email": user_data["email"],
            "tier_level": user_data["tier_level"],
            "tier_name": user_data["tier_name"],
            "department": user_data.get("department"),
            "created_at": user_data["created_at"].isoformat() if hasattr(user_data["created_at"], 'isoformat') else str(user_data["created_at"])
        },
        "files": {
            "folder": PROTECTED_FOLDER,
            "decrypted": decrypted_files,
            "decrypted_count": len(decrypted_files),
            "restricted": restricted_files,
            "restricted_count": len(restricted_files),
            "message": f"🔓 Decrypted {len(decrypted_files)} files for Tier {tier_level}"
        }
    }


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """
    Logout and re-encrypt all decrypted files.
    
    Cleans up decrypted files from the protected folder.
    """
    # 🔒 RE-ENCRYPT ALL DECRYPTED FILES
    reencrypted = reencrypt_all_decrypted()
    
    return {
        "message": "Logged out successfully",
        "files_reencrypted": len(reencrypted),
        "reencrypted": reencrypted
    }


@router.get("/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """
    Get current user's profile.
    
    Requires valid JWT token in Authorization header.
    """
    return UserResponse(
        id=user["id"],
        email=user["email"],
        tier_level=user["tier_level"],
        tier_name=user["tier_name"],
        department=user.get("department"),
        created_at=user["created_at"]
    )


@router.get("/tiers")
async def get_tiers():
    """
    Get all tier definitions.
    
    Returns tier levels with names, descriptions, and access patterns.
    """
    tiers = get_all_tiers()
    return {
        "tiers": [
            {
                "level": level,
                "name": info["name"],
                "description": info["description"],
                "patterns": info["patterns"]
            }
            for level, info in tiers.items()
        ]
    }
