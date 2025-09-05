## **Техническое задание для Claude Code на реализацию MVP бекенда AI Chat Platform**

### **Обзор проекта**

Необходимо создать упрощенный бекенд для AI чат-платформы, интегрирующий Letta (для stateful агентов с памятью) и LiteLLM (для управления биллингом). Каждый пользователь получает персонального AI-агента с долговременной памятью, который помнит всю историю взаимодействий.

### **Развернутые сервисы**

- **Letta Server**: `https://lettalettalatest-production-4de4.up.railway.app/`
- **LiteLLM Proxy**: `https://litellm-production-1c8b.up.railway.app/`
- **Supabase**: Используется для аутентификации и хранения данных

### **Архитектура системы**

Система состоит из FastAPI бекенда, который:
1. Управляет аутентификацией через Supabase Auth
2. Создает и управляет Letta агентами для каждого пользователя
3. Интегрирует биллинг через LiteLLM
4. Хранит историю сообщений для отображения в UI

### **Основные требования**

#### **1. Структура проекта**
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI приложение
│   ├── config.py            # Конфигурация и переменные окружения
│   ├── models/              # Pydantic модели
│   ├── services/            # Бизнес-логика
│   ├── routers/             # API эндпоинты
│   └── utils/               # Вспомогательные функции
├── requirements.txt
├── .env.example
└── README.md
```

#### **2. Модели данных (Supabase)**

```sql
-- Пользователи и агенты
CREATE TABLE user_profiles (
    id UUID REFERENCES auth.users(id) PRIMARY KEY,
    email TEXT,
    litellm_key TEXT UNIQUE,        -- API ключ пользователя от LiteLLM
    letta_agent_id TEXT UNIQUE,     -- ID агента в Letta
    agent_status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- История сообщений для UI
CREATE TABLE messages (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    tokens_used INTEGER,
    cost DECIMAL(10, 6),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Метрики использования
CREATE TABLE usage_metrics (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES user_profiles(id) ON DELETE CASCADE,
    date DATE DEFAULT CURRENT_DATE,
    total_messages INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    total_cost DECIMAL(10, 6) DEFAULT 0,
    UNIQUE(user_id, date)
);
```

#### **3. API Эндпоинты**

##### **Аутентификация**
- `POST /api/v1/auth/register` - Регистрация нового пользователя
- `POST /api/v1/auth/login` - Вход пользователя
- `POST /api/v1/auth/refresh` - Обновление токена
- `GET /api/v1/auth/me` - Текущий пользователь

##### **Чат с агентом**
- `POST /api/v1/chat/message` - Отправка сообщения агенту (с поддержкой streaming через SSE)
- `GET /api/v1/chat/history` - Получение истории сообщений (с пагинацией)
- `WS /api/v1/chat/stream` - WebSocket для real-time общения

##### **Управление агентом**
- `GET /api/v1/agent/status` - Статус агента пользователя
- `GET /api/v1/agent/memory` - Информация о памяти агента

##### **Пользователь**
- `GET /api/v1/user/profile` - Профиль пользователя
- `GET /api/v1/user/usage` - Статистика использования и расходы

#### **4. Процесс регистрации пользователя**

1. Пользователь регистрируется через Supabase Auth
2. В callback регистрации:
   - Создается запись в `user_profiles`
   - Вызывается LiteLLM `/user/new` с `user_id` от Supabase - получаем персональный API ключ
   - Создается Letta агент через API с конфигурацией LLM, указывающей на LiteLLM proxy с ключом пользователя
   - Сохраняется `letta_agent_id` в профиле пользователя

#### **5. Конфигурация Letta Agent**

При создании агента используется следующая конфигурация:

```python
{
    "name": f"agent-{user_id}",
    "model": "litellm_proxy/gpt-4",  # Используем LiteLLM как провайдер
    "model_endpoint": "https://litellm-production-1c8b.up.railway.app/v1",
    "model_endpoint_type": "openai",
    "api_key": user_litellm_key,  # Персональный ключ пользователя
    "memory_blocks": [
        {
            "label": "human",
            "value": f"User's name: {user_name or 'Friend'}"
        },
        {
            "label": "persona",
            "value": "You are a helpful, intelligent assistant with perfect memory. You remember all conversations and can recall any detail from past interactions."
        }
    ],
    "tools": ["send_message", "core_memory_append", "core_memory_replace", "archival_memory_insert", "archival_memory_search"]
}
```

#### **6. Обработка сообщений**

Поток обработки:
1. Пользователь отправляет сообщение через `POST /api/v1/chat/message`
2. Сервер сохраняет сообщение пользователя в БД
3. Отправляет сообщение Letta агенту через API
4. Letta обрабатывает с учетом всей памяти
5. При вызове LLM используется LiteLLM с ключом пользователя (биллинг автоматический)
6. Ответ стримится обратно через SSE
7. Полный ответ сохраняется в БД с метриками (токены, стоимость)

#### **7. Интеграция с внешними API**

##### **Letta API**
- Использовать официальный Python SDK: `pip install letta-client`
- Для self-hosted Letta авторизация не требуется (или пустой токен)
- Базовый URL: `https://lettalettalatest-production-4de4.up.railway.app/`

##### **LiteLLM API**
- Создание пользователя: `POST /user/new` с body: `{"user_id": "supabase_user_id"}`
- Ответ содержит сгенерированный API ключ
- Использовать master key из переменных окружения для административных операций

##### **Supabase**
- Использовать официальный SDK: `pip install supabase`
- JWT токены для аутентификации
- RLS политики для безопасности данных

#### **8. Переменные окружения**

```env
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_KEY=

# Letta
LETTA_BASE_URL=https://lettalettalatest-production-4de4.up.railway.app
LETTA_API_TOKEN=  # Оставить пустым для self-hosted

# LiteLLM
LITELLM_BASE_URL=https://litellm-production-1c8b.up.railway.app
LITELLM_MASTER_KEY=

# FastAPI
SECRET_KEY=
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### **9. Обработка ошибок**

- Graceful degradation при недоступности сервисов
- Четкие сообщения об ошибках для пользователей
- Логирование всех критических операций
- Retry механизм для внешних API вызовов

#### **10. Важные детали реализации**

1. **Не используй моки или заглушки** - все интеграции должны быть рабочими
2. **Streaming ответов** - использовать Server-Sent Events для streaming от Letta
3. **Сохранение истории** - все сообщения должны сохраняться в БД для UI
4. **Биллинг** - каждый LLM вызов автоматически тарифицируется через LiteLLM
5. **Память агента** - Letta агент должен помнить всю историю взаимодействий

#### **11. Специальный промт для Letta**

В корне проекта будет файл `letta_developer_prompt.md` с официальным промтом от Letta для агентов-разработчиков. Ознакомься с ним перед началом работы - он содержит best practices для работы с Letta API.

### **Результат работы**

Полностью функциональный MVP бекенда, который:
- Позволяет пользователям регистрироваться и входить в систему
- Автоматически создает персонального AI-агента для каждого пользователя
- Обеспечивает чат с агентом через API с поддержкой streaming
- Сохраняет всю историю сообщений
- Корректно тарифицирует использование через LiteLLM
- Агент помнит всю историю взаимодействий с пользователем

**Начни с изучения документации Letta API и структуры проекта, затем приступай к реализации.**