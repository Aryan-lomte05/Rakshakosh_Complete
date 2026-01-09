# Auth module
from backend.auth.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    create_user,
    authenticate_user,
    get_user_by_id,
    get_user_by_email
)
from backend.auth.middleware import get_current_user, get_current_user_optional, require_tier
from backend.auth.auth_api import router as auth_router
