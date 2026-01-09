"""
JWT Authentication Middleware

Provides dependency injection for protected routes.
Extracts and validates JWT from Authorization header.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any

from backend.auth.auth_service import decode_access_token, get_user_by_id

# Security scheme for Swagger UI
security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """
    Dependency that extracts and validates the JWT token.
    
    Usage:
        @router.get("/protected")
        async def protected_route(user: dict = Depends(get_current_user)):
            return {"message": f"Hello {user['email']}"}
    """
    token = credentials.credentials
    
    # Decode the token
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Get user from database
    user_id = payload.get("sub")
    user = await get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False))
) -> Dict[str, Any] | None:
    """
    Optional authentication - returns None if no token provided.
    
    Usage for routes that work with or without auth.
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if not payload:
        return None
    
    user_id = payload.get("sub")
    return await get_user_by_id(user_id)


def require_tier(min_tier: int):
    """
    Dependency factory that requires a minimum tier level.
    
    Usage:
        @router.get("/admin-only")
        async def admin_route(user: dict = Depends(require_tier(4))):
            return {"message": "Admin access granted"}
    """
    async def tier_checker(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
        if user["tier_level"] < min_tier:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires tier {min_tier} or higher. Your tier: {user['tier_level']}"
            )
        return user
    
    return tier_checker
