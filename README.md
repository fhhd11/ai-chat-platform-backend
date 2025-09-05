# AI Chat Platform Backend

Backend API для AI Chat Platform с интеграцией Letta и LiteLLM.

## Архитектура

```
User → FastAPI Backend → Letta Agent → LLM Proxy → LiteLLM → Gemini API
```

### Ключевые компоненты

- **FastAPI Backend** - основное API
- **Letta** - статeful AI агенты с памятью
- **LiteLLM** - биллинг прокси для LLM провайдеров
- **LLM Proxy** - промежуточный слой для индивидуальных API ключей
- **Supabase** - аутентификация и база данных

## LLM Proxy Layer

Решает проблему индивидуального биллинга для каждого пользователя:

1. Каждый Letta агент настроен на уникальный proxy endpoint
2. Proxy получает запросы от Letta с глобальным ключом
3. Proxy проксирует запросы в LiteLLM с индивидуальным ключом пользователя
4. Биллинг работает корректно для каждого пользователя

## Переменные окружения

```env
# FastAPI Configuration
SECRET_KEY=your-super-secret-key
ENVIRONMENT=development
LOG_LEVEL=INFO

# Supabase Configuration
SUPABASE_URL=your-supabase-url
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Letta Configuration
LETTA_BASE_URL=your-letta-url
LETTA_API_TOKEN=your-letta-token
LETTA_GLOBAL_API_KEY=global-key-for-proxy

# LiteLLM Configuration  
LITELLM_BASE_URL=your-litellm-url
LITELLM_MASTER_KEY=your-litellm-master-key

# Backend Configuration
BACKEND_BASE_URL=your-backend-url

# JWT Configuration
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Регистрация пользователя
- `POST /api/v1/auth/login` - Авторизация

### Chat
- `POST /api/v1/chat/message` - Отправка сообщения агенту
- `GET /api/v1/chat/history` - История сообщений

### Agent Management
- `GET /api/v1/agent/status` - Статус агента
- `GET /api/v1/agent/memory` - Память агента

### User Management
- `GET /api/v1/user/profile` - Профиль пользователя
- `GET /api/v1/user/usage` - Статистика использования

### LLM Proxy (Internal)
- `POST /api/v1/llm-proxy/{agent_id}/chat/completions` - Proxy для LLM запросов
- `POST /api/v1/llm-proxy/{agent_id}/embeddings` - Proxy для embeddings
- `GET /api/v1/llm-proxy/{agent_id}/test` - Тест proxy

## Деплой

### Docker
```bash
docker-compose build
docker-compose up -d
```

### Railway
1. Подключить GitHub репозиторий
2. Настроить переменные окружения
3. Деплой произойдет автоматически

## Разработка

```bash
# Установка зависимостей
pip install -r requirements.txt

# Запуск в режиме разработки
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Тестирование

### Регистрация нового пользователя
```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123", "name": "Test User"}'
```

### Авторизация
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

### Отправка сообщения
```bash
curl -X POST "http://localhost:8000/api/v1/chat/message" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Hello! Can you introduce yourself?"}'
```

## Технологии

- **FastAPI** - веб-фреймворк
- **Pydantic** - валидация данных
- **SQLAlchemy** - ORM
- **Alembic** - миграции БД
- **Letta** - AI агенты
- **LiteLLM** - LLM прокси
- **Supabase** - BaaS
- **Docker** - контейнеризация
