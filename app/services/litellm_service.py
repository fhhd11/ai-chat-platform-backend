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
        """Create new user in LiteLLM with budget configuration and get their API key"""
        try:
            from app.config import settings
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Create user with budget configuration (remove budget_reset - not supported by LiteLLM API)
                user_data = {
                    "user_id": user_id,
                    "max_budget": settings.user_default_budget,
                    "budget_duration": settings.user_budget_duration
                }
                
                response = await client.post(
                    f"{self.base_url}/user/new",
                    headers=self.headers,
                    json=user_data
                )
                
                response.raise_for_status()
                data = response.json()
                
                # Extract API key from response
                api_key = data.get("key") or data.get("api_key") or data.get("token")
                
                if api_key:
                    logger.info(f"Created LiteLLM user {user_id} with ${settings.user_default_budget} budget and key: {api_key[:10]}...")
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

    async def get_user_usage(self, user_id: str, user_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get user usage statistics from LiteLLM"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Try different endpoints that LiteLLM might use
                endpoints_to_try = [
                    f"{self.base_url}/user/usage",
                    f"{self.base_url}/spend/tags",
                    f"{self.base_url}/spend/logs"
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        params = {"user_id": user_id}
                        if user_key and "spend" in endpoint:
                            # For spend endpoints, might need to query by key
                            params["key"] = user_key
                        
                        response = await client.get(
                            endpoint,
                            headers=self.headers,
                            params=params
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Standardize response format
                            if isinstance(data, list) and data:
                                # Aggregate data from list of records
                                total_cost = sum(item.get("cost", 0) for item in data)
                                total_requests = len(data)
                                return {"total_cost": total_cost, "total_requests": total_requests}
                            elif isinstance(data, dict):
                                # Return as-is if already in dict format
                                return {
                                    "total_cost": data.get("total_cost", data.get("cost", 0)),
                                    "total_requests": data.get("total_requests", data.get("requests", 0))
                                }
                    except Exception as endpoint_error:
                        logger.debug(f"Endpoint {endpoint} failed: {endpoint_error}")
                        continue
                
                # If all endpoints fail, return default
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

    async def update_user_budget(self, user_id: str, max_budget: float, duration: str = "1mo") -> bool:
        """Update user budget settings using /user/update endpoint"""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Use /user/update endpoint instead of /user/budget
                update_data = {
                    "user_id": user_id,
                    "max_budget": max_budget,
                    "budget_duration": duration
                }
                
                response = await client.post(
                    f"{self.base_url}/user/update", 
                    headers=self.headers,
                    json=update_data
                )
                
                if response.status_code in [200, 201]:
                    logger.info(f"Updated budget for user {user_id} to ${max_budget}")
                    return True
                else:
                    logger.error(f"Failed to update budget: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating user budget: {e}")
            return False

    async def get_user_budget(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user budget information using /user/info endpoint"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Use /user/info endpoint instead of /user/budget
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
                    logger.error(f"Failed to get budget: {response.status_code} - {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting user budget: {e}")
            return None

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