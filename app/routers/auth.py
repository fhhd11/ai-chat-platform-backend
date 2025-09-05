from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import HTTPAuthorizationCredentials
from app.models.auth import UserRegister, UserLogin, UserResponse, TokenResponse
from app.services.supabase_service import supabase_service
from app.services.litellm_service import litellm_service
from app.services.letta_service import letta_service
from app.utils.auth import security, verify_supabase_token, get_current_user
from app.models.user import UserProfile
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Register new user with automatic agent creation"""
    try:
        # Step 1: Create user via Supabase Auth Admin API
        user_id = await supabase_service.create_user_auth(user_data.email, user_data.password)
        
        # Step 2: Create user in LiteLLM and get API key
        litellm_key = await litellm_service.create_user(user_id)
        if not litellm_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create billing account"
            )
        
        # Step 3: Create Letta agent for user
        letta_agent_id = await letta_service.create_agent(
            user_id=user_id,
            user_name=user_data.name,
            litellm_key=litellm_key
        )
        
        # Step 4: Create user profile in database
        user_profile = await supabase_service.create_user_profile(
            user_id=user_id,
            email=user_data.email,
            litellm_key=litellm_key,
            letta_agent_id=letta_agent_id
        )
        
        logger.info(f"Successfully registered user {user_id}")
        
        # In a real implementation, Supabase would provide the actual tokens
        return TokenResponse(
            access_token="mock_access_token",  # Replace with real Supabase token
            expires_in=3600,
            user=UserResponse(
                id=user_profile.id,
                email=user_profile.email,
                name=user_data.name,
                created_at=user_profile.created_at
            )
        )
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {str(e)}"
        )


@router.post("/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Login user (handled by Supabase Auth on frontend)"""
    try:
        # Login via Supabase Auth (use regular client, not admin)
        response = supabase_service.client.auth.sign_in_with_password({
            "email": user_data.email,
            "password": user_data.password
        })
        
        if not response.user or not response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials"
            )
        
        # Get user profile from database
        user_profile = await supabase_service.get_user_profile(response.user.id)
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )
        
        logger.info(f"Successful login for user: {response.user.id}")
        
        return TokenResponse(
            access_token=response.session.access_token,
            expires_in=response.session.expires_in,
            user=UserResponse(
                id=user_profile.id,
                email=user_profile.email,
                name=None,
                created_at=user_profile.created_at
            )
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Refresh access token"""
    try:
        # Verify current token
        payload = verify_supabase_token(credentials.credentials)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        user_id = payload.get("sub")
        user_profile = await supabase_service.get_user_profile(user_id)
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # In a real implementation, you would refresh the token with Supabase
        return TokenResponse(
            access_token="new_mock_access_token",  # Replace with real refreshed token
            expires_in=3600,
            user=UserResponse(
                id=user_profile.id,
                email=user_profile.email,
                name=None,
                created_at=user_profile.created_at
            )
        )
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token refresh failed"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: UserProfile = Depends(get_current_user)):
    """Get current user information"""
    try:
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            name=None,  # Add name field to UserProfile model if needed
            created_at=current_user.created_at
        )
        
    except Exception as e:
        logger.error(f"Get user info error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user information"
        )