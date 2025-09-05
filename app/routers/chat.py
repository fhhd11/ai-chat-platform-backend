from fastapi import APIRouter, HTTPException, status, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from app.models.chat import MessageCreate, Message, ChatResponse, ChatHistoryResponse, StreamChunk
from app.models.user import UserProfile
from app.services.supabase_service import supabase_service
from app.services.letta_service import letta_service
from app.utils.auth import get_current_active_user
from typing import Optional
from decimal import Decimal
import json
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/message", response_model=ChatResponse)
async def send_message(
    message_data: MessageCreate,
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Send message to user's agent (non-streaming)"""
    try:
        if not current_user.letta_agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User agent not found"
            )
        
        # Save user message to database
        user_message = await supabase_service.save_message(
            user_id=current_user.id,
            role="user",
            content=message_data.content
        )
        
        # Get agent response (collect from stream)
        full_response = ""
        usage_stats = None
        
        async for chunk in letta_service.send_message(
            current_user.letta_agent_id, 
            message_data.content
        ):
            if chunk["type"] == "message" and chunk["content"]:
                full_response += chunk["content"]
            elif chunk["type"] == "done":
                full_response = chunk["content"] or full_response
                usage_stats = chunk["data"].get("usage_stats")
                break
            elif chunk["type"] == "error":
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Agent error: {chunk['content']}"
                )
        
        if not full_response:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="No response from agent"
            )
        
        # Save agent response to database
        tokens_used = usage_stats.get("total_tokens", 0) if usage_stats else 0
        cost = Decimal(str(usage_stats.get("cost", 0.0))) if usage_stats else Decimal("0.0")
        
        agent_message = await supabase_service.save_message(
            user_id=current_user.id,
            role="assistant",
            content=full_response,
            tokens_used=tokens_used,
            cost=cost
        )
        
        # Update usage metrics
        await supabase_service.update_usage_metrics(
            user_id=current_user.id,
            messages_count=2,  # user + assistant
            tokens_used=tokens_used,
            cost=cost
        )
        
        logger.info(f"Message processed for user {current_user.id}")
        
        return ChatResponse(
            message=agent_message,
            agent_response=full_response,
            usage_stats=usage_stats
        )
        
    except Exception as e:
        logger.error(f"Chat message error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process message: {str(e)}"
        )


@router.post("/stream")
async def send_message_stream(
    message_data: MessageCreate,
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Send message to user's agent with Server-Sent Events streaming"""
    try:
        if not current_user.letta_agent_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User agent not found"
            )
        
        # Save user message to database
        await supabase_service.save_message(
            user_id=current_user.id,
            role="user",
            content=message_data.content
        )
        
        async def generate_stream():
            full_response = ""
            usage_stats = None
            
            try:
                async for chunk in letta_service.send_message(
                    current_user.letta_agent_id, 
                    message_data.content
                ):
                    # Convert chunk to StreamChunk model
                    stream_chunk = StreamChunk(
                        type=chunk["type"],
                        content=chunk.get("content"),
                        data=chunk.get("data")
                    )
                    
                    # Accumulate response
                    if chunk["type"] == "message" and chunk["content"]:
                        full_response += chunk["content"]
                    elif chunk["type"] == "done":
                        full_response = chunk["content"] or full_response
                        usage_stats = chunk["data"].get("usage_stats")
                    
                    # Yield SSE event
                    yield {
                        "data": stream_chunk.model_dump_json(),
                        "event": "message"
                    }
                    
                    # Break on completion
                    if chunk["type"] in ["done", "error"]:
                        break
                
                # Save agent response to database
                if full_response:
                    tokens_used = usage_stats.get("total_tokens", 0) if usage_stats else 0
                    cost = Decimal(str(usage_stats.get("cost", 0.0))) if usage_stats else Decimal("0.0")
                    
                    await supabase_service.save_message(
                        user_id=current_user.id,
                        role="assistant",
                        content=full_response,
                        tokens_used=tokens_used,
                        cost=cost
                    )
                    
                    # Update usage metrics
                    await supabase_service.update_usage_metrics(
                        user_id=current_user.id,
                        messages_count=2,
                        tokens_used=tokens_used,
                        cost=cost
                    )
                
                logger.info(f"Streamed message processed for user {current_user.id}")
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                error_chunk = StreamChunk(
                    type="error",
                    content=str(e),
                    data={"error": str(e)}
                )
                yield {
                    "data": error_chunk.model_dump_json(),
                    "event": "error"
                }
        
        return EventSourceResponse(generate_stream())
        
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start stream: {str(e)}"
        )


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    page: int = 1,
    page_size: int = 50,
    current_user: UserProfile = Depends(get_current_active_user)
):
    """Get paginated chat history for current user"""
    try:
        if page < 1:
            page = 1
        if page_size > 100:
            page_size = 100
        
        history_data = await supabase_service.get_chat_history(
            user_id=current_user.id,
            page=page,
            page_size=page_size
        )
        
        return ChatHistoryResponse(**history_data)
        
    except Exception as e:
        logger.error(f"Get chat history error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get chat history"
        )


@router.websocket("/stream")
async def websocket_chat(
    websocket: WebSocket,
    current_user: UserProfile = Depends(get_current_active_user)
):
    """WebSocket endpoint for real-time chat"""
    await websocket.accept()
    
    try:
        if not current_user.letta_agent_id:
            await websocket.send_json({
                "type": "error",
                "content": "User agent not found"
            })
            await websocket.close()
            return
        
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            message_content = data.get("message", "")
            
            if not message_content:
                await websocket.send_json({
                    "type": "error",
                    "content": "Empty message"
                })
                continue
            
            # Save user message
            await supabase_service.save_message(
                user_id=current_user.id,
                role="user",
                content=message_content
            )
            
            full_response = ""
            usage_stats = None
            
            # Stream agent response
            try:
                async for chunk in letta_service.send_message(
                    current_user.letta_agent_id, 
                    message_content
                ):
                    await websocket.send_json(chunk)
                    
                    if chunk["type"] == "message" and chunk["content"]:
                        full_response += chunk["content"]
                    elif chunk["type"] == "done":
                        full_response = chunk["content"] or full_response
                        usage_stats = chunk["data"].get("usage_stats")
                        break
                    elif chunk["type"] == "error":
                        break
                
                # Save agent response
                if full_response:
                    tokens_used = usage_stats.get("total_tokens", 0) if usage_stats else 0
                    cost = Decimal(str(usage_stats.get("cost", 0.0))) if usage_stats else Decimal("0.0")
                    
                    await supabase_service.save_message(
                        user_id=current_user.id,
                        role="assistant",
                        content=full_response,
                        tokens_used=tokens_used,
                        cost=cost
                    )
                    
                    await supabase_service.update_usage_metrics(
                        user_id=current_user.id,
                        messages_count=2,
                        tokens_used=tokens_used,
                        cost=cost
                    )
                
            except Exception as e:
                logger.error(f"WebSocket agent error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": str(e)
                })
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {current_user.id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error", 
                "content": str(e)
            })
            await websocket.close()
        except:
            pass