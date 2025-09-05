from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import httpx
import json
import logging
from typing import Dict, Any, AsyncIterator
from app.config import settings
from app.services.supabase_service import supabase_service
from app.models.user import UserProfile

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/llm-proxy")
security = HTTPBearer()


async def get_user_by_agent_id(agent_id: str) -> UserProfile:
    """Get user profile by agent_id"""
    user_profile = await supabase_service.get_user_by_agent_id(agent_id)
    if not user_profile:
        logger.error(f"No user found for agent_id: {agent_id}")
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return user_profile


async def verify_letta_request(credentials: HTTPAuthorizationCredentials = Depends(security)) -> bool:
    """Verify that request comes from Letta server"""
    if credentials.credentials != settings.letta_global_api_key:
        raise HTTPException(status_code=401, detail="Invalid Letta API key")
    return True


@router.post("/{agent_id}/chat/completions")
async def proxy_llm_request(
    agent_id: str, 
    request: Request,
    _: bool = Depends(verify_letta_request)
):
    """
    Proxy endpoint for Letta agents.
    Accepts requests from Letta and proxies them to LiteLLM with correct user API key.
    """
    try:
        # Get user profile by agent_id
        user_profile = await get_user_by_agent_id(agent_id)
        
        # Get request body
        request_body = await request.json()
        
        # Check if streaming is requested
        stream = request_body.get("stream", False)
        
        logger.info(f"Proxying LLM request for agent {agent_id}, user {user_profile.id}, stream={stream}")
        
        # Proxy request to LiteLLM
        if stream:
            return await proxy_streaming_request(request_body, user_profile.litellm_key)
        else:
            return await proxy_regular_request(request_body, user_profile.litellm_key)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in proxy_llm_request for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")


async def proxy_regular_request(request_body: Dict[str, Any], litellm_key: str) -> Dict[str, Any]:
    """Proxy regular (non-streaming) request to LiteLLM"""
    headers = {
        "Authorization": f"Bearer {litellm_key}",
        "Content-Type": "application/json"
    }
    
    litellm_url = f"{settings.litellm_base_url}/chat/completions"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                litellm_url,
                headers=headers,
                json=request_body
            )
            
            if response.status_code != 200:
                logger.error(f"LiteLLM error {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LiteLLM error: {response.text}"
                )
            
            return response.json()
            
        except httpx.TimeoutException:
            logger.error("Timeout connecting to LiteLLM")
            raise HTTPException(status_code=504, detail="LiteLLM timeout")
        except httpx.RequestError as e:
            logger.error(f"Request error to LiteLLM: {e}")
            raise HTTPException(status_code=502, detail=f"LiteLLM connection error: {str(e)}")


async def proxy_streaming_request(request_body: Dict[str, Any], litellm_key: str) -> StreamingResponse:
    """Proxy streaming request to LiteLLM"""
    headers = {
        "Authorization": f"Bearer {litellm_key}",
        "Content-Type": "application/json"
    }
    
    litellm_url = f"{settings.litellm_base_url}/chat/completions"
    
    async def stream_generator() -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                async with client.stream(
                    "POST",
                    litellm_url,
                    headers=headers,
                    json=request_body
                ) as response:
                    if response.status_code != 200:
                        error_text = await response.aread()
                        logger.error(f"LiteLLM streaming error {response.status_code}: {error_text}")
                        yield f"data: {json.dumps({'error': f'LiteLLM error: {error_text.decode()}'})}\n\n"
                        return
                    
                    async for chunk in response.aiter_text():
                        if chunk:
                            yield chunk
                            
            except httpx.TimeoutException:
                logger.error("Timeout in streaming request to LiteLLM")
                yield f"data: {json.dumps({'error': 'LiteLLM timeout'})}\n\n"
            except httpx.RequestError as e:
                logger.error(f"Streaming request error to LiteLLM: {e}")
                yield f"data: {json.dumps({'error': f'LiteLLM connection error: {str(e)}'})}\n\n"
    
    return StreamingResponse(
        stream_generator(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@router.post("/{agent_id}/embeddings")
async def proxy_embeddings_request(
    agent_id: str,
    request: Request,
    _: bool = Depends(verify_letta_request)
):
    """Proxy embeddings request to LiteLLM"""
    try:
        # Get user profile by agent_id
        user_profile = await get_user_by_agent_id(agent_id)
        
        # Get request body
        request_body = await request.json()
        
        logger.info(f"Proxying embeddings request for agent {agent_id}, user {user_profile.id}")
        
        headers = {
            "Authorization": f"Bearer {user_profile.litellm_key}",
            "Content-Type": "application/json"
        }
        
        litellm_url = f"{settings.litellm_base_url}/embeddings"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                litellm_url,
                headers=headers,
                json=request_body
            )
            
            if response.status_code != 200:
                logger.error(f"LiteLLM embeddings error {response.status_code}: {response.text}")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"LiteLLM embeddings error: {response.text}"
                )
            
            return response.json()
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in proxy_embeddings_request for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Embeddings proxy error: {str(e)}")


@router.get("/{agent_id}/test")
async def test_proxy(agent_id: str):
    """Test endpoint to verify agent_id → user mapping"""
    try:
        user_profile = await get_user_by_agent_id(agent_id)
        
        return {
            "agent_id": agent_id,
            "user_id": user_profile.id,
            "user_name": user_profile.name,
            "has_litellm_key": bool(user_profile.litellm_key),
            "litellm_key_prefix": user_profile.litellm_key[:10] + "..." if user_profile.litellm_key else None
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in test_proxy for agent {agent_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))