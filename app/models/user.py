from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date
from decimal import Decimal


class UserProfile(BaseModel):
    id: str
    email: EmailStr
    litellm_key: Optional[str] = None
    letta_agent_id: Optional[str] = None
    agent_status: str = "active"
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class UsageMetrics(BaseModel):
    id: str
    user_id: str
    date: date
    total_messages: int = 0
    total_tokens: int = 0
    total_cost: Decimal = Decimal("0.0")
    
    class Config:
        from_attributes = True


class UserUsageResponse(BaseModel):
    profile: UserProfile
    today_usage: UsageMetrics
    total_usage: dict[str, str]