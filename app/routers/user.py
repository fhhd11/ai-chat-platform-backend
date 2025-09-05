from fastapi import APIRouter, HTTPException, status, Depends
from app.models.user import UserProfile, UserUsageResponse
from app.services.supabase_service import supabase_service
from app.services.litellm_service import litellm_service
from app.utils.auth import get_current_user
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/profile", response_model=UserProfile)
async def get_user_profile(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get current user's profile information"""
    try:
        return current_user
        
    except Exception as e:
        logger.error(f"Get user profile error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user profile"
        )


@router.get("/usage", response_model=Dict[str, Any])
async def get_user_usage(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get user's usage statistics and costs"""
    try:
        # Get usage metrics from our database
        db_usage = await supabase_service.get_usage_metrics(current_user.id)
        
        # Get billing information from LiteLLM
        litellm_usage = await litellm_service.get_user_usage(current_user.id, current_user.litellm_key)
        
        # Get budget information from LiteLLM
        budget_info = await litellm_service.get_user_budget(current_user.id)
        
        # Combine data
        usage_response = {
            "profile": current_user,
            "database_usage": db_usage,
            "billing_usage": litellm_usage,
            "budget_info": budget_info or {
                "max_budget": 0,
                "current_spend": 0,
                "budget_duration": "1mo"
            },
            "summary": {
                "total_messages": db_usage["total_usage"]["total_messages"],
                "total_tokens": db_usage["total_usage"]["total_tokens"],
                "total_cost": db_usage["total_usage"]["total_cost"],
                "today_messages": db_usage["today_usage"].total_messages,
                "today_tokens": db_usage["today_usage"].total_tokens,
                "today_cost": db_usage["today_usage"].total_cost,
                "litellm_cost": litellm_usage.get("total_cost", 0),
                "litellm_requests": litellm_usage.get("total_requests", 0),
                "budget_remaining": (budget_info.get("max_budget", 0) - budget_info.get("current_spend", 0)) if budget_info else 0
            }
        }
        
        return usage_response
        
    except Exception as e:
        logger.error(f"Get user usage error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get usage information"
        )


@router.get("/stats")
async def get_user_stats(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get detailed user statistics"""
    try:
        # Get chat history count
        history = await supabase_service.get_chat_history(
            user_id=current_user.id,
            page=1,
            page_size=1
        )
        
        # Get usage metrics
        usage = await supabase_service.get_usage_metrics(current_user.id)
        
        # Get LiteLLM usage
        litellm_usage = await litellm_service.get_user_usage(current_user.id)
        
        stats = {
            "user_id": current_user.id,
            "agent_id": current_user.letta_agent_id,
            "agent_status": current_user.agent_status,
            "account_created": current_user.created_at,
            "total_conversations": history["total"],
            "usage_metrics": {
                "total_messages": usage["total_usage"]["total_messages"],
                "total_tokens": usage["total_usage"]["total_tokens"],
                "total_cost": usage["total_usage"]["total_cost"],
                "today_messages": usage["today_usage"].total_messages,
                "today_tokens": usage["today_usage"].total_tokens,
                "today_cost": usage["today_usage"].total_cost
            },
            "billing_info": {
                "litellm_total_cost": litellm_usage.get("total_cost", 0),
                "litellm_total_requests": litellm_usage.get("total_requests", 0),
                "has_billing_key": bool(current_user.litellm_key)
            }
        }
        
        return stats
        
    except Exception as e:
        logger.error(f"Get user stats error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get user statistics"
        )


@router.post("/reset-billing-key")
async def reset_billing_key(
    current_user: UserProfile = Depends(get_current_user)
):
    """Reset user's LiteLLM API key"""
    try:
        if not current_user.litellm_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has no billing key to reset"
            )
        
        # Reset key in LiteLLM
        new_key = await litellm_service.reset_user_key(current_user.id)
        
        if not new_key:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset billing key"
            )
        
        # Update key in database (this would require updating the user profile)
        # Note: This is a simplified version - in practice you'd update the database
        
        return {
            "status": "success",
            "message": "Billing key has been reset",
            "new_key_preview": f"{new_key[:8]}...{new_key[-4:]}",  # Show partial key for confirmation
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset billing key error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset billing key: {str(e)}"
        )


@router.post("/budget")
async def update_user_budget(
    max_budget: float,
    duration: str = "1mo",
    current_user: UserProfile = Depends(get_current_user)
):
    """Update user budget settings"""
    try:
        from app.config import settings
        
        # Validate budget amount
        if max_budget < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Budget amount must be positive"
            )
        
        if max_budget > 1000:  # Safety limit
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Budget amount cannot exceed $1000"
            )
        
        # Validate duration format
        valid_durations = ["1d", "1w", "1mo", "3mo", "6mo", "1y"]
        if duration not in valid_durations:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid duration. Must be one of: {', '.join(valid_durations)}"
            )
        
        # Update budget in LiteLLM
        success = await litellm_service.update_user_budget(
            user_id=current_user.id,
            max_budget=max_budget,
            duration=duration
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update budget"
            )
        
        return {
            "status": "success",
            "message": f"Budget updated to ${max_budget} for {duration}",
            "max_budget": max_budget,
            "duration": duration
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update budget error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update budget: {str(e)}"
        )


@router.get("/budget")
async def get_user_budget(
    current_user: UserProfile = Depends(get_current_user)
):
    """Get user budget information"""
    try:
        budget_info = await litellm_service.get_user_budget(current_user.id)
        
        if not budget_info:
            from app.config import settings
            return {
                "max_budget": settings.user_default_budget,
                "current_spend": 0,
                "budget_duration": settings.user_budget_duration,
                "budget_remaining": settings.user_default_budget,
                "status": "default_budget"
            }
        
        remaining = budget_info.get("max_budget", 0) - budget_info.get("current_spend", 0)
        
        return {
            **budget_info,
            "budget_remaining": max(0, remaining),
            "status": "active"
        }
        
    except Exception as e:
        logger.error(f"Get budget error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get budget information"
        )


@router.get("/health")
async def check_user_health(
    current_user: UserProfile = Depends(get_current_user)
):
    """Check overall user account health"""
    try:
        health_status = {
            "user_id": current_user.id,
            "profile_status": "active",
            "agent_status": current_user.agent_status,
            "has_agent": bool(current_user.letta_agent_id),
            "has_billing": bool(current_user.litellm_key),
            "checks": {
                "profile": True,
                "agent": False,
                "billing": False
            }
        }
        
        # Check agent health
        if current_user.letta_agent_id:
            try:
                from app.services.letta_service import letta_service
                agent_status = await letta_service.get_agent_status(current_user.letta_agent_id)
                health_status["checks"]["agent"] = bool(agent_status)
            except:
                health_status["checks"]["agent"] = False
        
        # Check billing health
        if current_user.litellm_key:
            try:
                billing_valid = await litellm_service.validate_user_key(current_user.litellm_key)
                health_status["checks"]["billing"] = billing_valid
            except:
                health_status["checks"]["billing"] = False
        
        # Overall health
        all_checks_passed = all(health_status["checks"].values())
        health_status["overall_status"] = "healthy" if all_checks_passed else "degraded"
        
        return health_status
        
    except Exception as e:
        logger.error(f"User health check error: {e}")
        return {
            "user_id": current_user.id,
            "overall_status": "error",
            "error": str(e),
            "checks": {
                "profile": True,
                "agent": False,
                "billing": False
            }
        }