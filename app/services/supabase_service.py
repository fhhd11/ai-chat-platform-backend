from supabase import create_client, Client
from app.config import settings
from app.models.user import UserProfile, UsageMetrics
from app.models.chat import Message
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class SupabaseService:
    def __init__(self):
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_anon_key
        )
        self.admin_client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_key
        )

    async def create_user_auth(self, email: str, password: str) -> str:
        """Create user via Supabase Auth Admin API"""
        try:
            # Use admin client to create user via Auth API
            response = self.admin_client.auth.admin.create_user({
                "email": email,
                "password": password,
                "email_confirm": True
            })
            
            if response.user:
                return response.user.id
            else:
                raise Exception("Failed to create user via Auth API")
                
        except Exception as e:
            logger.error(f"Error creating user via Auth: {e}")
            raise

    async def create_user_profile(self, user_id: str, email: str, litellm_key: str, letta_agent_id: str) -> UserProfile:
        """Create user profile after registration"""
        try:
            data = {
                "id": user_id,
                "email": email,
                "litellm_key": litellm_key,
                "letta_agent_id": letta_agent_id,
                "agent_status": "active"
            }
            
            result = self.admin_client.table("user_profiles").upsert(data).execute()
            
            if result.data:
                profile_data = result.data[0]
                return UserProfile(**profile_data)
            else:
                raise Exception("Failed to create user profile")
                
        except Exception as e:
            logger.error(f"Error creating user profile: {e}")
            raise

    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """Get user profile by ID"""
        try:
            result = self.admin_client.table("user_profiles").select("*").eq("id", user_id).execute()
            
            if result.data:
                return UserProfile(**result.data[0])
            return None
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            raise

    async def update_agent_status(self, user_id: str, status: str) -> bool:
        """Update agent status for user"""
        try:
            result = self.admin_client.table("user_profiles").update({
                "agent_status": status,
                "updated_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            
            return len(result.data) > 0
            
        except Exception as e:
            logger.error(f"Error updating agent status: {e}")
            raise

    async def save_message(self, user_id: str, role: str, content: str, 
                          tokens_used: Optional[int] = None, 
                          cost: Optional[Decimal] = None) -> Message:
        """Save chat message to database"""
        try:
            data = {
                "user_id": user_id,
                "role": role,
                "content": content,
                "tokens_used": tokens_used,
                "cost": float(cost) if cost else None
            }
            
            result = self.admin_client.table("messages").insert(data).execute()
            
            if result.data:
                message_data = result.data[0]
                return Message(**message_data)
            else:
                raise Exception("Failed to save message")
                
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            raise

    async def get_chat_history(self, user_id: str, page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Get paginated chat history for user"""
        try:
            offset = (page - 1) * page_size
            
            # Get total count
            count_result = self.admin_client.table("messages").select("*", count="exact").eq("user_id", user_id).execute()
            total = count_result.count or 0
            
            # Get messages
            result = self.admin_client.table("messages")\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .range(offset, offset + page_size - 1)\
                .execute()
            
            messages = [Message(**msg) for msg in result.data] if result.data else []
            
            return {
                "messages": messages,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_next": offset + page_size < total
            }
            
        except Exception as e:
            logger.error(f"Error getting chat history: {e}")
            raise

    async def update_usage_metrics(self, user_id: str, messages_count: int = 1, 
                                 tokens_used: int = 0, cost: Decimal = Decimal("0.0")):
        """Update daily usage metrics"""
        try:
            today = date.today()
            
            # Try to get existing record
            result = self.admin_client.table("usage_metrics")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("date", today.isoformat())\
                .execute()
            
            if result.data:
                # Update existing record
                existing = result.data[0]
                updated_data = {
                    "total_messages": existing["total_messages"] + messages_count,
                    "total_tokens": existing["total_tokens"] + tokens_used,
                    "total_cost": float(Decimal(str(existing["total_cost"])) + cost)
                }
                
                self.admin_client.table("usage_metrics")\
                    .update(updated_data)\
                    .eq("id", existing["id"])\
                    .execute()
            else:
                # Create new record
                new_data = {
                    "user_id": user_id,
                    "date": today.isoformat(),
                    "total_messages": messages_count,
                    "total_tokens": tokens_used,
                    "total_cost": float(cost)
                }
                
                self.admin_client.table("usage_metrics").insert(new_data).execute()
                
        except Exception as e:
            logger.error(f"Error updating usage metrics: {e}")
            raise

    async def get_usage_metrics(self, user_id: str) -> Dict[str, Any]:
        """Get usage metrics for user"""
        try:
            today = date.today()
            
            # Get today's usage
            today_result = self.admin_client.table("usage_metrics")\
                .select("*")\
                .eq("user_id", user_id)\
                .eq("date", today.isoformat())\
                .execute()
            
            today_usage = UsageMetrics(**today_result.data[0]) if today_result.data else UsageMetrics(
                id="", user_id=user_id, date=today
            )
            
            # Get total usage
            total_result = self.admin_client.table("usage_metrics")\
                .select("total_messages, total_tokens, total_cost")\
                .eq("user_id", user_id)\
                .execute()
            
            total_messages = sum(row["total_messages"] for row in total_result.data) if total_result.data else 0
            total_tokens = sum(row["total_tokens"] for row in total_result.data) if total_result.data else 0
            total_cost = sum(Decimal(str(row["total_cost"])) for row in total_result.data) if total_result.data else Decimal("0.0")
            
            return {
                "today_usage": today_usage,
                "total_usage": {
                    "total_messages": total_messages,
                    "total_tokens": total_tokens,
                    "total_cost": total_cost
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting usage metrics: {e}")
            raise

    async def get_user_by_agent_id(self, agent_id: str) -> Optional[UserProfile]:
        """Get user profile by letta_agent_id"""
        try:
            result = self.admin_client.table("user_profiles")\
                .select("*")\
                .eq("letta_agent_id", agent_id)\
                .execute()
            
            if result.data:
                user_data = result.data[0]
                return UserProfile(**user_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting user by agent_id {agent_id}: {e}")
            return None


# Global instance
supabase_service = SupabaseService()