"""
Pydantic Models for Authentication and Users

Defines request/response schemas for:
- User signup and login
- User profile
- JWT tokens
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


# =============================================================================
# REQUEST MODELS
# =============================================================================

class UserSignupRequest(BaseModel):
    """Request body for user signup."""
    email: EmailStr
    password: str = Field(..., min_length=8, description="Minimum 8 characters")
    tier_level: int = Field(default=1, ge=1, le=4, description="Access tier (1-4)")
    department: Optional[str] = None


class UserLoginRequest(BaseModel):
    """Request body for user login."""
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Request body for changing password."""
    current_password: str
    new_password: str = Field(..., min_length=8)


# =============================================================================
# RESPONSE MODELS
# =============================================================================

class UserResponse(BaseModel):
    """User profile response (no sensitive data)."""
    id: str
    email: str
    tier_level: int
    tier_name: str
    department: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    """Response after successful login."""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class SignupResponse(BaseModel):
    """Response after successful signup."""
    message: str
    user: UserResponse


# =============================================================================
# INTERNAL MODELS (Database)
# =============================================================================

class UserInDB(BaseModel):
    """User document as stored in MongoDB."""
    email: str
    password_hash: str
    tier_level: int
    department: Optional[str] = None
    encryption_key_id: Optional[str] = None  # Reference to key in vault
    created_at: datetime
    last_login: Optional[datetime] = None
