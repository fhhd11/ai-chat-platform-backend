# AI Chat Platform API - Документация

## Обзор

Это backend API для AI Chat Platform - персонализированной платформы чата с ИИ, которая использует Letta для создания агентов с долгосрочной памятью и LiteLLM для управления биллингом.

## Базовый URL

```
Production: https://ai-chat-backend-production.up.railway.app
Local: http://localhost:8000
```

## Аутентификация

API использует JWT токены для аутентификации через Supabase Auth.

Все защищенные endpoints требуют заголовок:
```
Authorization: Bearer <jwt_token>
```

## Endpoints

### 1. Аутентификация (`/api/v1/auth`)

#### POST `/api/v1/auth/register`
Регистрация нового пользователя

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (201):**
```json
{
  "status": "success",
  "message": "User registered successfully",
  "user": {
    "id": "user_id",
    "email": "user@example.com",
    "created_at": "2025-01-01T00:00:00Z"
  },
  "tokens": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token"
  },
  "agent_info": {
    "agent_id": "letta_agent_id",
    "status": "created"
  }
}
```

#### POST `/api/v1/auth/login`
Авторизация пользователя

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response (200):**
```json
{
  "status": "success",
  "user": {
    "id": "user_id",
    "email": "user@example.com"
  },
  "tokens": {
    "access_token": "jwt_token",
    "refresh_token": "refresh_token"
  }
}
```

#### GET `/api/v1/auth/me`
Получить информацию о текущем пользователе

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "created_at": "2025-01-01T00:00:00Z",
  "letta_agent_id": "agent_id",
  "litellm_key": "llm_api_key",
  "agent_status": "active"
}
```

### 2. Чат (`/api/v1/chat`)

#### POST `/api/v1/chat/message`
Отправить сообщение агенту (с потоковым ответом)

**Headers:** 
- `Authorization: Bearer <token>`
- `Accept: text/event-stream` (для потокового ответа)

**Request Body:**
```json
{
  "content": "Привет! Как дела?"
}
```

**Response (потоковый SSE):**
```
data: {"type": "message_start", "message": {"id": "msg_id", "role": "assistant"}}

data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}

data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Привет"}}

data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "! Отлично"}}

data: {"type": "message_end", "message": {"usage": {"input_tokens": 10, "output_tokens": 15, "total_tokens": 25}}}
```

**Response (обычный):**
```json
{
  "status": "success",
  "response": {
    "content": "Привет! Отлично, спасибо! Как дела у тебя?",
    "usage": {
      "input_tokens": 10,
      "output_tokens": 15,
      "total_tokens": 25,
      "estimated_cost": 0.001
    }
  },
  "message_id": "msg_id"
}
```

#### GET `/api/v1/chat/history`
Получить историю сообщений

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**
- `page` (int, default=1): Номер страницы
- `page_size` (int, default=50): Размер страницы

**Response (200):**
```json
{
  "messages": [
    {
      "id": "msg_id",
      "user_message": "Привет!",
      "assistant_response": "Привет! Как дела?",
      "created_at": "2025-01-01T12:00:00Z",
      "usage_metrics": {
        "input_tokens": 10,
        "output_tokens": 15,
        "total_tokens": 25,
        "cost": 0.001
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total": 100,
    "pages": 2
  }
}
```

### 3. Управление агентом (`/api/v1/agent`)

#### GET `/api/v1/agent/status`
Получить статус агента

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "agent_id": "agent_id",
  "status": "active",
  "created_at": "2025-01-01T00:00:00Z",
  "last_updated": "2025-01-01T12:00:00Z",
  "name": "AI Assistant",
  "persona": "Helpful AI assistant",
  "human": "User description",
  "tools": ["send_message", "core_memory_append", "archival_memory_search"]
}
```

#### GET `/api/v1/agent/memory`
Получить память агента

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "core_memory": {
    "persona": "I am a helpful AI assistant...",
    "human": "User is interested in technology..."
  },
  "recall_memory": {
    "total_messages": 150,
    "recent_messages": [
      {
        "id": "msg_id",
        "role": "user",
        "content": "Hello!",
        "timestamp": "2025-01-01T12:00:00Z"
      }
    ]
  },
  "archival_memory": {
    "total_passages": 25,
    "recent_passages": [
      {
        "id": "passage_id",
        "text": "Important information...",
        "timestamp": "2025-01-01T11:00:00Z"
      }
    ]
  }
}
```

#### POST `/api/v1/agent/memory`
Обновить память агента

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "persona": "Updated persona description",
  "human": "Updated human description"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "Agent memory updated successfully",
  "updated_memory": {
    "persona": "Updated persona description",
    "human": "Updated human description"
  }
}
```

#### POST `/api/v1/agent/reset`
Сбросить агента (создать нового)

**Headers:** `Authorization: Bearer <token>`

**Request Body (опционально):**
```json
{
  "persona": "Custom persona",
  "human": "Custom human description"
}
```

**Response (200):**
```json
{
  "status": "success",
  "message": "Agent reset successfully",
  "new_agent": {
    "agent_id": "new_agent_id",
    "status": "created",
    "persona": "AI Assistant persona",
    "human": "Human description"
  }
}
```

### 4. Пользователь (`/api/v1/user`)

#### GET `/api/v1/user/profile`
Получить профиль пользователя

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "id": "user_id",
  "email": "user@example.com",
  "created_at": "2025-01-01T00:00:00Z",
  "letta_agent_id": "agent_id",
  "litellm_key": "llm_api_key",
  "agent_status": "active"
}
```

#### GET `/api/v1/user/usage`
Получить статистику использования

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "profile": {
    "id": "user_id",
    "email": "user@example.com"
  },
  "database_usage": {
    "total_usage": {
      "total_messages": 100,
      "total_tokens": 15000,
      "total_cost": 5.25
    },
    "today_usage": {
      "total_messages": 10,
      "total_tokens": 1500,
      "total_cost": 0.52
    }
  },
  "billing_usage": {
    "total_cost": 5.25,
    "total_requests": 100
  },
  "budget_info": {
    "max_budget": 10.0,
    "current_spend": 5.25,
    "budget_duration": "1mo",
    "budget_reset_at": "2025-02-01T00:00:00Z"
  },
  "summary": {
    "total_messages": 100,
    "total_tokens": 15000,
    "total_cost": 5.25,
    "today_messages": 10,
    "today_tokens": 1500,
    "today_cost": 0.52,
    "litellm_cost": 5.25,
    "litellm_requests": 100,
    "budget_remaining": 4.75
  }
}
```

#### GET `/api/v1/user/stats`
Получить детальную статистику пользователя

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "user_id": "user_id",
  "agent_id": "agent_id",
  "agent_status": "active",
  "account_created": "2025-01-01T00:00:00Z",
  "total_conversations": 50,
  "usage_metrics": {
    "total_messages": 100,
    "total_tokens": 15000,
    "total_cost": 5.25,
    "today_messages": 10,
    "today_tokens": 1500,
    "today_cost": 0.52
  },
  "billing_info": {
    "litellm_total_cost": 5.25,
    "litellm_total_requests": 100,
    "has_billing_key": true
  }
}
```

#### GET `/api/v1/user/budget`
Получить информацию о бюджете

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "max_budget": 10.0,
  "current_spend": 5.25,
  "budget_duration": "1mo",
  "budget_remaining": 4.75,
  "budget_reset_at": "2025-02-01T00:00:00Z",
  "status": "active"
}
```

#### POST `/api/v1/user/budget`
Обновить настройки бюджета

**Headers:** `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "max_budget": 20.0,
  "duration": "1mo"
}
```

**Query Parameters:**
- `max_budget` (float): Максимальный бюджет (0-1000)
- `duration` (str): Длительность ("1d", "1w", "1mo", "3mo", "6mo", "1y")

**Response (200):**
```json
{
  "status": "success",
  "message": "Budget updated to $20.0 for 1mo",
  "max_budget": 20.0,
  "duration": "1mo"
}
```

#### POST `/api/v1/user/reset-billing-key`
Сбросить API ключ для биллинга

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "status": "success",
  "message": "Billing key has been reset",
  "new_key_preview": "sk-1234...abcd"
}
```

#### GET `/api/v1/user/health`
Проверить состояние аккаунта пользователя

**Headers:** `Authorization: Bearer <token>`

**Response (200):**
```json
{
  "user_id": "user_id",
  "profile_status": "active",
  "agent_status": "active",
  "has_agent": true,
  "has_billing": true,
  "overall_status": "healthy",
  "checks": {
    "profile": true,
    "agent": true,
    "billing": true
  }
}
```

### 5. Системные endpoints

#### GET `/health`
Проверка здоровья API

**Response (200):**
```json
{
  "status": "healthy",
  "service": "AI Chat Platform API",
  "version": "1.0.0",
  "environment": "production"
}
```

#### GET `/`
Корневой endpoint

**Response (200):**
```json
{
  "message": "AI Chat Platform API",
  "version": "1.0.0",
  "docs": "Not available in production"
}
```

## Коды ошибок

### 400 Bad Request
```json
{
  "detail": "Invalid request data"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Not enough permissions"
}
```

### 404 Not Found
```json
{
  "detail": "Resource not found"
}
```

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

## Rate Limiting

API не имеет явных ограничений по частоте запросов, но использование ограничено бюджетом пользователя в LiteLLM.

## Потоковые ответы (Server-Sent Events)

Endpoint `/api/v1/chat/message` поддерживает потоковые ответы через Server-Sent Events (SSE).

Для получения потокового ответа используйте заголовок:
```
Accept: text/event-stream
```

Типы событий:
- `message_start`: Начало сообщения
- `content_block_start`: Начало блока контента
- `content_block_delta`: Частичное обновление контента
- `content_block_stop`: Конец блока контента
- `message_end`: Конец сообщения с метриками использования

## Примеры интеграции

### JavaScript/TypeScript
```javascript
// Регистрация пользователя
const register = async (email, password) => {
  const response = await fetch('https://ai-chat-backend-production.up.railway.app/api/v1/auth/register', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  
  return await response.json();
};

// Отправка сообщения с потоковым ответом
const sendMessage = async (token, content) => {
  const response = await fetch('https://ai-chat-backend-production.up.railway.app/api/v1/chat/message', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({ content })
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = JSON.parse(line.slice(6));
        console.log('Received:', data);
      }
    }
  }
};
```

### Python
```python
import requests
import json

# Регистрация пользователя
def register(email, password):
    response = requests.post(
        'https://ai-chat-backend-production.up.railway.app/api/v1/auth/register',
        json={'email': email, 'password': password}
    )
    return response.json()

# Получение статистики использования
def get_usage_stats(token):
    response = requests.get(
        'https://ai-chat-backend-production.up.railway.app/api/v1/user/usage',
        headers={'Authorization': f'Bearer {token}'}
    )
    return response.json()
```