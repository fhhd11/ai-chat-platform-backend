from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class MemoryBlock(BaseModel):
    label: str
    value: str
    description: Optional[str] = None


class AgentConfig(BaseModel):
    name: str
    model: str = "litellm_proxy/gpt-4"
    model_endpoint: str
    model_endpoint_type: str = "openai"
    api_key: str
    memory_blocks: List[MemoryBlock]
    tools: List[str] = [
        "send_message", 
        "core_memory_append", 
        "core_memory_replace", 
        "archival_memory_insert", 
        "archival_memory_search"
    ]


class AgentStatus(BaseModel):
    agent_id: str
    status: str
    created_at: datetime
    last_updated: datetime
    memory_usage: Optional[Dict[str, Any]] = None


class AgentMemoryInfo(BaseModel):
    agent_id: str
    memory_blocks: List[MemoryBlock]
    archival_memory_count: Optional[int] = None
    last_updated: datetime