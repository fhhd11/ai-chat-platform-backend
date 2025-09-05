import httpx
from app.config import settings
from typing import Optional, Dict, Any
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LiteLLMService:
    def __init__(self):
        self.base_url = settings.litellm_base_url
        self.master_key = settings.litellm_master_key
        self.headers = {
            "Authorization": f"Bearer {self.master_key}",
            "Content-Type": "application/json"
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_user(self, user_id: str) -> Optional[str]:
        """Create new user in LiteLLM and get their API key"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/user/new",
                    headers=self.headers,
                    json={"user_id": user_id}
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extract API key from response
                api_key = data.get("key") or data.get("api_key") or data.get("token")
                
                if api_key:
                    logger.info(f"Created LiteLLM user {user_id} with key: {api_key[:10]}..." if api_key else "NO KEY")
                    return api_key
                else:
                    logger.error(f"No API key in LiteLLM response: {data}")
                    raise ValueError("No API key returned from LiteLLM")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating LiteLLM user: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error creating LiteLLM user: {e}")
            raise

    async def get_user_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user information from LiteLLM"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user/info",
                    headers=self.headers,
                    params={"user_id": user_id}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return None
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                logger.error(f"HTTP error getting user info: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
            raise

    async def get_user_usage(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user usage statistics from LiteLLM"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/user/usage",
                    headers=self.headers,
                    params={"user_id": user_id}
                )
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 404:
                    return {"total_cost": 0, "total_requests": 0}
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            if e.response.status_code != 404:
                logger.error(f"HTTP error getting user usage: {e.response.status_code} - {e.response.text}")
            return {"total_cost": 0, "total_requests": 0}
        except Exception as e:
            logger.error(f"Error getting user usage: {e}")
            return {"total_cost": 0, "total_requests": 0}

    async def validate_user_key(self, user_key: str) -> bool:
        """Validate user API key with LiteLLM"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/key/info",
                    headers={
                        "Authorization": f"Bearer {user_key}",
                        "Content-Type": "application/json"
                    }
                )
                
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Error validating user key: {e}")
            return False

    async def reset_user_key(self, user_id: str) -> Optional[str]:
        """Reset user API key"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/user/reset",
                    headers=self.headers,
                    json={"user_id": user_id}
                )
                
                response.raise_for_status()
                data = response.json()
                
                new_key = data.get("key") or data.get("api_key") or data.get("token")
                
                if new_key:
                    logger.info(f"Reset API key for user {user_id}")
                    return new_key
                else:
                    raise ValueError("No new API key returned from LiteLLM")
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error resetting user key: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error resetting user key: {e}")
            raise

    async def delete_user(self, user_id: str) -> bool:
        """Delete user from LiteLLM"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/user/delete",
                    headers=self.headers,
                    json={"user_id": user_id}
                )
                
                # Consider both 200 and 404 as success (user deleted or doesn't exist)
                if response.status_code in [200, 404]:
                    logger.info(f"Deleted user {user_id} from LiteLLM")
                    return True
                else:
                    response.raise_for_status()
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error deleting user: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error deleting user: {e}")
            raise

    async def health_check(self) -> bool:
        """Check if LiteLLM service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
                
        except Exception as e:
            logger.error(f"LiteLLM health check failed: {e}")
            return False


# Global instance
litellm_service = LiteLLMService()