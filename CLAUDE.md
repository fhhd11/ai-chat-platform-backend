# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a backend for an AI Chat Platform MVP that integrates Letta (for stateful agents with memory) and LiteLLM (for billing management). The system creates personalized AI agents for each user that maintain long-term memory of all interactions.

## Architecture

The system consists of a FastAPI backend that:
1. Manages authentication through Supabase Auth
2. Creates and manages Letta agents for each user
3. Integrates billing through LiteLLM proxy
4. Stores message history for UI display

### External Services Integration

- **Letta Server**: `https://lettalettalatest-production-4de4.up.railway.app/` (stateful agents)
- **LiteLLM Proxy**: `https://litellm-production-1c8b.up.railway.app/` (billing management)
- **Supabase**: Authentication and data storage

## Expected Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration and environment variables
│   ├── models/              # Pydantic models
│   ├── services/            # Business logic
│   ├── routers/             # API endpoints
│   └── utils/               # Helper functions
├── requirements.txt
├── .env.example
└── README.md
```

## Core Development Commands

Since this is a Python FastAPI project, use these commands:

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run with auto-reload for development
python -m app.main

# Install additional packages
pip install package_name
pip freeze > requirements.txt
```

## Key Implementation Requirements

### User Registration Flow
1. User registers through Supabase Auth
2. Create record in `user_profiles` table
3. Call LiteLLM `/user/new` to get personal API key
4. Create Letta agent with LiteLLM configuration
5. Store `letta_agent_id` in user profile

### Letta Agent Configuration
Agents are configured with:
- Model: `litellm_proxy/gpt-4` via LiteLLM endpoint
- Personal API key for billing
- Memory blocks: `human`, `persona` with contextual information
- Tools: `send_message`, `core_memory_append`, `core_memory_replace`, `archival_memory_insert`, `archival_memory_search`

### Message Processing Flow
1. User sends message via `POST /api/v1/chat/message`
2. Save user message to database
3. Send to Letta agent (maintains conversation context)
4. Stream response via Server-Sent Events
5. Save full response with usage metrics (tokens, cost)

## API Integration Specifics

### Letta SDK Usage
```python
from letta_client import Letta

# Self-hosted Letta (no auth required)
client = Letta(base_url="https://lettalettalatest-production-4de4.up.railway.app")
```

### LiteLLM Integration
- Create user: `POST /user/new` with `{"user_id": "supabase_user_id"}`
- Use master key for admin operations
- Personal API keys auto-handle billing

### Supabase Integration
```python
from supabase import create_client
# JWT tokens for authentication
# RLS policies for data security
```

## Database Schema

Key tables:
- `user_profiles`: User data with `litellm_key` and `letta_agent_id`
- `messages`: Chat history with usage metrics
- `usage_metrics`: Daily aggregated usage statistics

## Environment Variables Required

```env
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# Letta
LETTA_BASE_URL=https://lettalettalatest-production-4de4.up.railway.app
LETTA_API_TOKEN=  # Leave empty for self-hosted

# LiteLLM
LITELLM_BASE_URL=https://litellm-production-1c8b.up.railway.app
LITELLM_MASTER_KEY=

# FastAPI
SECRET_KEY=
ENVIRONMENT=development
LOG_LEVEL=INFO
```

## Important Implementation Notes

1. **No mocks or stubs** - All integrations must be functional
2. **Streaming responses** - Use Server-Sent Events for Letta streaming
3. **Complete message history** - Save all messages to database for UI
4. **Automatic billing** - LLM calls auto-billed through LiteLLM
5. **Stateful agents** - Letta agents remember entire interaction history
6. **Error handling** - Implement graceful degradation and retry mechanisms

## Letta Development Guidelines

The project includes `letta_developer_prompt.md` with official Letta best practices. Key points:
- Agents are stateful services, not stateless APIs
- Send only single user messages (not conversation history)
- Use proper memory blocks with descriptions
- Handle different message types in responses
- Configure agents with correct LiteLLM proxy settings

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `GET /api/v1/auth/me` - Current user info

### Chat
- `POST /api/v1/chat/message` - Send message (with SSE streaming)
- `GET /api/v1/chat/history` - Message history (paginated)

### Agent Management
- `GET /api/v1/agent/status` - Agent status
- `GET /api/v1/agent/memory` - Agent memory info

### User
- `GET /api/v1/user/profile` - User profile
- `GET /api/v1/user/usage` - Usage statistics and costs