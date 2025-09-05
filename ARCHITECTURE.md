# AI Chat Platform - Архитектура проекта

## Обзор системы

AI Chat Platform - это backend система для персонализированной платформы чата с ИИ, которая создает уникальных агентов для каждого пользователя с долгосрочной памятью всех взаимодействий.

## Архитектурная схема

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│                 │    │                 │    │                 │
│   Frontend      │◄──►│   FastAPI       │◄──►│   Letta         │
│   (React/Next)  │    │   Backend       │    │   Server        │
│                 │    │                 │    │   (Agents)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │                 │    │                 │
                       │   Supabase      │    │   LiteLLM       │
                       │   (Auth + DB)   │    │   (Billing)     │
                       │                 │    │                 │
                       └─────────────────┘    └─────────────────┘
```

## Основные компоненты

### 1. FastAPI Backend (app/)

Центральное приложение, которое:
- Обрабатывает HTTP запросы от фронтенда
- Управляет аутентификацией через JWT токены
- Интегрируется с внешними сервисами
- Обеспечивает потоковые ответы через Server-Sent Events

**Структура:**
```
app/
├── main.py              # Основное приложение FastAPI
├── config.py            # Конфигурация и переменные окружения
├── models/              # Pydantic модели для валидации данных
│   ├── user.py
│   ├── chat.py
│   └── agent.py
├── routers/             # API endpoints, разделенные по функциональности
│   ├── auth.py          # Аутентификация и регистрация
│   ├── chat.py          # Чат с агентами
│   ├── agent.py         # Управление агентами
│   ├── user.py          # Профиль и статистика пользователя
│   └── llm_proxy.py     # Прокси для LLM запросов
├── services/            # Бизнес-логика и интеграции
│   ├── supabase_service.py    # Работа с базой данных
│   ├── letta_service.py       # Интеграция с Letta
│   └── litellm_service.py     # Интеграция с LiteLLM
└── utils/               # Вспомогательные функции
    └── auth.py          # JWT токены и аутентификация
```

### 2. Letta Server (Внешний сервис)

Letta (ранее MemGPT) - это сервис для создания статeful агентов с долгосрочной памятью.

**URL:** `https://lettalettalatest-production-4de4.up.railway.app`

**Особенности:**
- Каждый пользователь получает персональный агент
- Агенты помнят все предыдущие взаимодействия
- Поддержка core memory (persona, human) и archival memory
- Инструменты для работы с памятью и поиском

**Конфигурация агентов:**
- Model: `litellm_proxy/gpt-4`
- Endpoint: LiteLLM proxy для биллинга
- Memory blocks: persona (описание ИИ), human (описание пользователя)
- Tools: send_message, core_memory_append, core_memory_replace, archival_memory_insert, archival_memory_search

### 3. LiteLLM Proxy (Внешний сервис)

LiteLLM - это прокси-сервер для управления биллингом и ограничениями LLM запросов.

**URL:** `https://litellm-production-1c8b.up.railway.app`

**Функции:**
- Создание пользователей с индивидуальными API ключами
- Отслеживание использования (токены, стоимость, запросы)
- Управление бюджетами пользователей
- Автоматический биллинг за каждый запрос к LLM

**API для управления:**
- `/user/new` - создание пользователя с бюджетом
- `/user/info` - получение информации о пользователе и бюджете
- `/user/update` - обновление настроек бюджета
- `/user/usage` - статистика использования

### 4. Supabase (База данных + Auth)

Supabase обеспечивает аутентификацию пользователей и хранение данных.

**Компоненты:**
- **Supabase Auth:** JWT токены, регистрация, авторизация
- **PostgreSQL:** Реляционная база данных
- **Row Level Security (RLS):** Безопасность на уровне строк

**Основные таблицы:**
```sql
-- Профили пользователей
user_profiles (
  id UUID PRIMARY KEY,           -- ID из Supabase Auth
  email TEXT,
  letta_agent_id TEXT,          -- ID агента в Letta
  litellm_key TEXT,             -- Персональный API ключ для биллинга
  agent_status TEXT,
  created_at TIMESTAMP
);

-- История сообщений
messages (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES user_profiles(id),
  user_message TEXT,
  assistant_response TEXT,
  message_metadata JSONB,      -- Дополнительные данные от Letta
  usage_metrics JSONB,         -- Токены, стоимость
  created_at TIMESTAMP
);

-- Агрегированная статистика использования
usage_metrics (
  id UUID PRIMARY KEY,
  user_id UUID REFERENCES user_profiles(id),
  date DATE,
  total_messages INTEGER,
  total_tokens INTEGER,
  total_cost DECIMAL,
  created_at TIMESTAMP
);
```

## Потоки данных

### 1. Регистрация пользователя

```
1. Frontend → Backend: POST /api/v1/auth/register
2. Backend → Supabase: Создание пользователя в Auth
3. Backend → Supabase: Создание записи в user_profiles
4. Backend → LiteLLM: POST /user/new (создание пользователя с бюджетом)
5. Backend → Letta: Создание персонального агента
6. Backend → Supabase: Обновление user_profiles с agent_id и litellm_key
7. Backend → Frontend: Ответ с JWT токенами и информацией об агенте
```

### 2. Отправка сообщения

```
1. Frontend → Backend: POST /api/v1/chat/message (SSE stream)
2. Backend → Supabase: Сохранение пользовательского сообщения
3. Backend → Letta: Отправка сообщения агенту пользователя
4. Letta → Backend: Потоковый ответ с частичными данными
5. Backend → Frontend: Server-Sent Events с частичными ответами
6. Backend → Supabase: Сохранение полного ответа с метриками использования
7. Backend → Supabase: Обновление агрегированной статистики
```

### 3. Получение статистики

```
1. Frontend → Backend: GET /api/v1/user/usage
2. Backend → Supabase: Запрос статистики из базы данных
3. Backend → LiteLLM: Запрос биллинговой информации
4. Backend → Frontend: Объединенные данные о использовании
```

## Безопасность

### Аутентификация
- JWT токены от Supabase Auth
- Автоматическая валидация токенов на каждом запросе
- Row Level Security (RLS) для защиты данных пользователей

### API Keys
- Каждый пользователь получает персональный LiteLLM ключ
- Ключи используются только для биллинга, не передаются во фронтенд
- Мастер-ключ LiteLLM используется только для административных операций

### CORS
- Настройка разрешенных доменов
- Поддержка credentials для JWT токенов

## Масштабирование и производительность

### Асинхронность
- Все операции с базой данных и внешними API асинхронные
- Использование httpx для HTTP клиентов вместо синхронных библиотек

### Потоковые ответы
- Server-Sent Events для реального времени
- Минимизация задержек при получении ответов от агентов

### Кеширование
- Возможность добавления Redis для кеширования сессий
- Агенты Letta сами кешируют контекст разговора

### Мониторинг
- Логирование всех операций
- Health check endpoints для контроля состояния сервисов
- Метрики использования в реальном времени

## Развертывание

### Production (Railway)
```bash
# Основное приложение
https://ai-chat-backend-production.up.railway.app

# Переменные окружения
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_KEY=...
LETTA_BASE_URL=https://lettalettalatest-production-4de4.up.railway.app
LITELLM_BASE_URL=https://litellm-production-1c8b.up.railway.app
LITELLM_MASTER_KEY=...
USER_DEFAULT_BUDGET=10.0
USER_BUDGET_DURATION=1mo
```

### Local Development
```bash
# Запуск локально
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Переменные окружения в .env файле
cp .env.example .env
# Заполнить необходимые ключи
```

### Docker
```bash
# Сборка образа
docker build -t ai-chat-backend .

# Запуск с переменными окружения
docker run -p 8000:8000 --env-file .env ai-chat-backend
```

## Интеграция с фронтендом

### Основные endpoint'ы для фронтенда:

1. **Аутентификация:**
   - `POST /api/v1/auth/register` - регистрация
   - `POST /api/v1/auth/login` - вход
   - `GET /api/v1/auth/me` - текущий пользователь

2. **Чат:**
   - `POST /api/v1/chat/message` - отправка сообщения (SSE)
   - `GET /api/v1/chat/history` - история сообщений

3. **Профиль пользователя:**
   - `GET /api/v1/user/profile` - профиль
   - `GET /api/v1/user/usage` - статистика использования
   - `GET /api/v1/user/budget` - информация о бюджете
   - `POST /api/v1/user/budget` - обновление бюджета

4. **Управление агентом:**
   - `GET /api/v1/agent/status` - статус агента
   - `GET /api/v1/agent/memory` - память агента
   - `POST /api/v1/agent/memory` - обновление памяти
   - `POST /api/v1/agent/reset` - сброс агента

### Примеры интеграции:

**React hooks для чата:**
```javascript
const useChatStream = (token) => {
  const [messages, setMessages] = useState([]);
  
  const sendMessage = async (content) => {
    const response = await fetch('/api/v1/chat/message', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream'
      },
      body: JSON.stringify({ content })
    });
    
    const reader = response.body.getReader();
    // Обработка потокового ответа...
  };
};
```

**TypeScript типы:**
```typescript
interface User {
  id: string;
  email: string;
  created_at: string;
  letta_agent_id: string;
  agent_status: string;
}

interface Message {
  id: string;
  user_message: string;
  assistant_response: string;
  created_at: string;
  usage_metrics: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    cost: number;
  };
}

interface UsageStats {
  total_messages: number;
  total_tokens: number;
  total_cost: number;
  budget_remaining: number;
}
```

## Будущие улучшения

### Функциональность
- Поддержка файлов в сообщениях (изображения, документы)
- Экспорт истории чата
- Тонкая настройка личности агента через UI
- Поддержка голосового ввода/вывода

### Техническая архитектура
- Микросервисная архитектура для масштабирования
- Redis для кеширования сессий и rate limiting
- WebSocket альтернатива для реального времени
- Система уведомлений (email, push)

### Мониторинг и аналитика
- Продвинутые метрики использования
- A/B тестирование для улучшения UX
- Автоматические алерты при ошибках
- Дашборд для административного управления