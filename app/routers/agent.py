from fastapi import APIRouter, HTTPException, status, Depends
from app.models.agent import AgentStatus, AgentMemoryInfo
from app.models.user import UserProfile
from app.services.letta_service import letta_service
from app.utils.auth import get_current_active_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/status", response_model=AgentStatus)
async def get_agent_status(
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Get current user's agent status"""
    try:
        if not current_user.letta_agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User agent not found"
            )
        
        agent_status = await letta_service.get_agent_status(current_user.letta_agent_id)
        
        if not agent_status:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent not found in Letta"
            )
        
        return agent_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get agent status error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent status"
        )


@router.get("/memory", response_model=AgentMemoryInfo)
async def get_agent_memory(
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Get current user's agent memory information"""
    try:
        if not current_user.letta_agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User agent not found"
            )
        
        memory_info = await letta_service.get_agent_memory(current_user.letta_agent_id)
        
        if not memory_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Agent memory not found"
            )
        
        return memory_info
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get agent memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get agent memory"
        )


@router.get("/health")
async def check_agent_health(
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Check if user's agent is healthy and responsive"""
    try:
        if not current_user.letta_agent_id:
            return {
                "status": "error",
                "message": "No agent assigned to user",
                "agent_id": None
            }
        
        # Try to get agent status
        agent_status = await letta_service.get_agent_status(current_user.letta_agent_id)
        
        if agent_status:
            return {
                "status": "healthy",
                "message": "Agent is responsive",
                "agent_id": current_user.letta_agent_id,
                "agent_status": agent_status.status
            }
        else:
            return {
                "status": "error", 
                "message": "Agent not found or not responding",
                "agent_id": current_user.letta_agent_id
            }
        
    except Exception as e:
        logger.error(f"Agent health check error: {e}")
        return {
            "status": "error",
            "message": f"Health check failed: {str(e)}",
            "agent_id": current_user.letta_agent_id
        }


@router.post("/reset")
async def reset_agent_memory(
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Reset agent memory to default state (advanced operation)"""
    try:
        if not current_user.letta_agent_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User agent not found"
            )
        
        # This is a simplified reset - in practice you might want more granular control
        from app.models.agent import MemoryBlock
        
        default_memory = [
            MemoryBlock(
                label="human",
                value="User's name: Friend"
            ),
            MemoryBlock(
                label="persona", 
                value="You are a helpful, intelligent assistant with perfect memory. You remember all conversations and can recall any detail from past interactions."
            )
        ]
        
        success = await letta_service.update_agent_memory(
            current_user.letta_agent_id,
            default_memory
        )
        
        if success:
            return {
                "status": "success",
                "message": "Agent memory has been reset to default state",
                "agent_id": current_user.letta_agent_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to reset agent memory"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Reset agent memory error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reset agent memory: {str(e)}"
        )