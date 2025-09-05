from letta_client import Letta
from app.config import settings
from app.models.agent import AgentConfig, AgentStatus, AgentMemoryInfo, MemoryBlock
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class LettaService:
    def __init__(self):
        # Create Letta client with standard configuration
        self.client = Letta(
            base_url=settings.letta_base_url,
            token=settings.letta_api_token  # Can be None for self-hosted
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def create_agent(self, user_id: str, user_name: Optional[str], litellm_key: str) -> str:
        """Create a new Letta agent for user"""
        try:
            logger.info(f"Creating agent with LiteLLM key: {litellm_key[:10]}..." if litellm_key else "NO KEY PROVIDED")
            config = AgentConfig(
                name=f"agent-{user_id}",
                model_endpoint=f"{settings.litellm_base_url}/v1",
                api_key=litellm_key,
                memory_blocks=[
                    MemoryBlock(
                        label="human",
                        value=f"User's name: {user_name or 'Friend'}"
                    ),
                    MemoryBlock(
                        label="persona",
                        value="You are a helpful, intelligent assistant with perfect memory. You remember all conversations and can recall any detail from past interactions."
                    )
                ]
            )
            
            # First create agent with basic config to get the ID
            agent = self.client.agents.create(
                memory_blocks=[
                    {
                        "label": block.label,
                        "value": block.value,
                        "description": block.description
                    }
                    for block in config.memory_blocks
                ],
                tools=config.tools,
                # Minimal LLM config required for creation
                llm_config={
                    "model": "gpt-4o",
                    "model_endpoint_type": "openai",
                    "context_window": 128000
                },
                # Minimal embedding config required for creation  
                embedding_config={
                    "embedding_model": "text-embedding-ada-002",
                    "embedding_endpoint_type": "openai",
                    "embedding_dim": 1536
                }
            )
            
            logger.info(f"Created Letta agent {agent.id} for user {user_id}")
            
            # Now modify the agent with proper proxy endpoints using actual agent ID
            modified_agent = self.client.agents.modify(
                agent_id=agent.id,
                llm_config={
                    "model": "gpt-4o",
                    "model_endpoint_type": "openai",
                    "model_endpoint": f"{settings.backend_base_url}/api/v1/llm-proxy/{agent.id}",
                    "provider_name": "proxy",
                    "context_window": 128000
                },
                embedding_config={
                    "embedding_model": "text-embedding-ada-002",
                    "embedding_endpoint_type": "openai",
                    "embedding_endpoint": f"{settings.backend_base_url}/api/v1/llm-proxy/{agent.id}",
                    "provider_name": "proxy",
                    "embedding_dim": 1536
                }
            )
            
            logger.info(f"Modified Letta agent {agent.id} with proper proxy endpoints")
            return agent.id
            
        except Exception as e:
            logger.error(f"Error creating Letta agent: {e}")
            raise

    async def send_message(self, agent_id: str, message: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Send message to agent and stream response using direct HTTP calls"""
        import httpx
        import json
        
        try:
            # Create async HTTP client with extended timeout
            async with httpx.AsyncClient(timeout=300.0) as client:
                # Prepare request data
                request_data = {
                    "messages": [{"role": "user", "content": message}],
                    "stream_tokens": True
                }
                
                # Make streaming request to Letta
                url = f"{settings.letta_base_url}/v1/agents/{agent_id}/messages/stream"
                headers = {"Content-Type": "application/json"}
                if settings.letta_api_token:
                    headers["Authorization"] = f"Bearer {settings.letta_api_token}"
                
                logger.info(f"Sending async streaming request to Letta: {url}")
                
                full_response = ""
                usage_stats = None
                
                async with client.stream("POST", url, json=request_data, headers=headers) as response:
                    if response.status_code != 200:
                        error_msg = f"Letta API error {response.status_code}: {await response.aread()}"
                        logger.error(error_msg)
                        yield {
                            "type": "error",
                            "content": error_msg,
                            "data": {"error": error_msg}
                        }
                        return
                    
                    # Process streaming response
                    async for line in response.aiter_lines():
                        if not line.strip():
                            continue
                            
                        # Parse Server-Sent Events format
                        if line.startswith("data: "):
                            try:
                                data_str = line[6:]  # Remove "data: " prefix
                                if data_str == "[DONE]":
                                    break
                                    
                                chunk_data = json.loads(data_str)
                                message_type = chunk_data.get("message_type", "")
                                
                                if message_type == "assistant_message" and chunk_data.get("content"):
                                    content = chunk_data["content"]
                                    full_response += content
                                    yield {
                                        "type": "message",
                                        "content": content,
                                        "data": {
                                            "message_type": message_type,
                                            "full_response": full_response
                                        }
                                    }
                                
                                elif message_type == "reasoning_message" and chunk_data.get("reasoning"):
                                    yield {
                                        "type": "reasoning",
                                        "content": chunk_data["reasoning"],
                                        "data": {"message_type": message_type}
                                    }
                                
                                elif message_type == "tool_call_message":
                                    tool_call = chunk_data.get("tool_call", {})
                                    yield {
                                        "type": "tool_call",
                                        "content": f"Tool: {tool_call.get('name', 'unknown')}",
                                        "data": {
                                            "message_type": message_type,
                                            "tool_name": tool_call.get("name"),
                                            "tool_arguments": tool_call.get("arguments")
                                        }
                                    }
                                
                                elif message_type == "usage_statistics":
                                    usage_stats = {
                                        "total_tokens": chunk_data.get('total_tokens', 0),
                                        "prompt_tokens": chunk_data.get('prompt_tokens', 0),
                                        "completion_tokens": chunk_data.get('completion_tokens', 0),
                                        "cost": chunk_data.get('cost', 0.0)
                                    }
                                    yield {
                                        "type": "usage",
                                        "content": None,
                                        "data": usage_stats
                                    }
                                    
                            except json.JSONDecodeError as je:
                                logger.warning(f"Failed to parse streaming chunk: {line}, error: {je}")
                                continue
                
                # Send final response
                yield {
                    "type": "done",
                    "content": full_response,
                    "data": {
                        "full_response": full_response,
                        "usage_stats": usage_stats
                    }
                }
            
        except Exception as e:
            logger.error(f"Error sending message to agent {agent_id}: {e}")
            yield {
                "type": "error",
                "content": str(e),
                "data": {"error": str(e)}
            }

    async def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Get agent status and info"""
        try:
            # List all agents and find the specific one
            agents = self.client.agents.list()
            agent = next((a for a in agents if a.id == agent_id), None)
            
            if agent:
                return AgentStatus(
                    agent_id=agent.id,
                    status="active",
                    created_at=agent.created_at,
                    last_updated=agent.last_updated,
                    memory_usage={}
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent status: {e}")
            raise

    async def get_agent_memory(self, agent_id: str) -> Optional[AgentMemoryInfo]:
        """Get agent memory information"""
        try:
            agent = self.client.agents.get(agent_id)
            
            if agent:
                memory_blocks = []
                
                # Get memory blocks
                for block in agent.memory_blocks:
                    memory_blocks.append(MemoryBlock(
                        label=block.label,
                        value=block.value,
                        description=block.description
                    ))
                
                return AgentMemoryInfo(
                    agent_id=agent.id,
                    memory_blocks=memory_blocks,
                    last_updated=agent.last_updated
                )
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting agent memory: {e}")
            raise

    async def update_agent_memory(self, agent_id: str, memory_blocks: List[MemoryBlock]) -> bool:
        """Update agent memory blocks"""
        try:
            for block in memory_blocks:
                # Update memory block using Letta client
                self.client.agents.memory.update(
                    agent_id=agent_id,
                    memory_block={
                        "label": block.label,
                        "value": block.value,
                        "description": block.description
                    }
                )
            
            logger.info(f"Updated memory for agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating agent memory: {e}")
            raise

    async def delete_agent(self, agent_id: str) -> bool:
        """Delete agent"""
        try:
            self.client.agents.delete(agent_id)
            logger.info(f"Deleted agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting agent: {e}")
            raise


# Global instance
letta_service = LettaService()