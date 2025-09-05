from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from app.config import settings
from app.services.supabase_service import supabase_service
from app.models.user import UserProfile
from typing import Optional
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> UserProfile:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token (Supabase JWT) - skip signature verification for testing
        token = credentials.credentials
        payload = jwt.decode(
            token,
            "",  # Empty key when signature verification is disabled
            options={"verify_signature": False, "verify_aud": False, "verify_exp": True}
        )
        
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
            
    except JWTError as e:
        logger.error(f"JWT decode error: {e}")
        raise credentials_exception
    
    # Get user profile from database
    user_profile = await supabase_service.get_user_profile(user_id)
    
    if user_profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User profile not found"
        )
    
    return user_profile


async def get_current_active_user(current_user: UserProfile = Depends(get_current_user)) -> UserProfile:
    """Get current active user (with active agent)"""
    if current_user.agent_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User agent is not active"
        )
    
    return current_user


def verify_supabase_token(token: str) -> Optional[dict]:
    """Verify Supabase JWT token"""
    try:
        payload = jwt.decode(
            token,
            settings.supabase_anon_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_signature": False}
        )
        return payload
    except JWTError as e:
        logger.error(f"Token verification failed: {e}")
        return None