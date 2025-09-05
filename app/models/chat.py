from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime
from decimal import Decimal


class MessageCreate(BaseModel):
    content: str


class Message(BaseModel):
    id: str
    user_id: str
    role: Literal["user", "assistant"]
    content: str
    tokens_used: Optional[int] = None
    cost: Optional[Decimal] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    message: Message
    agent_response: str
    usage_stats: Optional[dict] = None


class ChatHistoryResponse(BaseModel):
    messages: List[Message]
    total: int
    page: int
    page_size: int
    has_next: bool


class StreamChunk(BaseModel):
    type: Literal["message", "usage", "error", "done"]
    content: Optional[str] = None
    data: Optional[dict] = None