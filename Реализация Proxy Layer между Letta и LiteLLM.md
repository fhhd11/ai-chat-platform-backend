## **Задание для Claude Code: Реализация Proxy Layer между Letta и LiteLLM**

### **Описание проблемы**

При разработке MVP мы обнаружили архитектурное ограничение Letta: невозможно указать индивидуальный API ключ провайдера для каждого агента. Letta использует глобальные настройки для API ключей, что не позволяет нам реализовать персональный биллинг через LiteLLM для каждого пользователя.

### **Найденное решение**

Мы будем использовать возможность Letta указывать кастомный `model_endpoint` для каждого агента. Создадим промежуточный proxy слой в нашем FastAPI бекенде, который:

1. Предоставит уникальный endpoint для каждого агента
2. Будет принимать запросы от Letta с глобальным ключом
3. Проксировать их в LiteLLM с правильным ключом пользователя

### **Архитектура решения**

```
Letta Agent → Custom Endpoint (наш FastAPI) → LiteLLM Proxy (с ключом пользователя) → LLM Provider
```

### **Техническая реализация**

#### **1. Создание уникального endpoint для агента**

При создании Letta агента указываем кастомную LLM конфигурацию:

```python
llm_config = {
    "model": "gpt-4",
    "model_endpoint_type": "openai",  # Letta будет думать что это OpenAI-compatible endpoint
    "model_endpoint": f"https://your-backend-url.com/api/v1/llm-proxy/{agent_id}/chat/completions",
    "context_window": 8192
}
```

#### **2. Реализация proxy endpoint в FastAPI**

Добавь новый роутер `llm_proxy.py`:

```python
# app/routers/llm_proxy.py

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
import httpx
import json

router = APIRouter(prefix="/api/v1/llm-proxy")

@router.post("/{agent_id}/chat/completions")
async def proxy_llm_request(agent_id: str, request: Request):
    """
    Proxy endpoint для Letta агента.
    Принимает запросы от Letta и проксирует их в LiteLLM с правильным ключом пользователя.
    """
    # 1. Получить user_id по agent_id из БД
    # 2. Получить litellm_key пользователя
    # 3. Проксировать запрос в LiteLLM с правильным ключом
    # 4. Вернуть ответ обратно в Letta (с поддержкой streaming)
```

#### **3. Ключевые моменты реализации**

##### **Аутентификация запросов от Letta**
- Letta будет отправлять запросы с глобальным API ключом (из переменных окружения Letta сервера)
- Добавь проверку этого ключа через специальный header или bearer token
- Храни этот глобальный ключ в переменных окружения как `LETTA_GLOBAL_API_KEY`

##### **Маппинг agent_id → user_id → litellm_key**
```python
async def get_user_litellm_key_by_agent(agent_id: str) -> str:
    """
    Получает LiteLLM ключ пользователя по agent_id
    """
    # Запрос в БД через Supabase
    # SELECT litellm_key FROM user_profiles WHERE letta_agent_id = agent_id
```

##### **Проксирование запроса**
```python
async def proxy_to_litellm(request_body: dict, user_litellm_key: str, stream: bool = False):
    """
    Проксирует запрос в LiteLLM с правильным ключом
    """
    headers = {
        "Authorization": f"Bearer {user_litellm_key}",
        "Content-Type": "application/json"
    }
    
    litellm_url = f"{LITELLM_BASE_URL}/chat/completions"
    
    if stream:
        # Реализовать streaming через httpx
        # Вернуть StreamingResponse
    else:
        # Обычный запрос
        # Вернуть JSON response
```

##### **Поддержка streaming**
- Letta может запрашивать streaming ответы (параметр `stream: true` в body)
- Используй `httpx` для проксирования streaming запросов
- Возвращай `StreamingResponse` с правильными headers

##### **Обработка ошибок**
- Если agent_id не найден → 404
- Если litellm_key не найден → 500 с понятным сообщением
- Если LiteLLM вернул ошибку → проксировать ее обратно в Letta
- Логировать все запросы для отладки

#### **4. Обновление процесса создания агента**

В сервисе создания агента (`agent_service.py`) обнови логику:

```python
async def create_agent_for_user(user_id: str, user_name: str) -> dict:
    """
    Создает Letta агента для пользователя с кастомным LLM endpoint
    """
    # 1. Генерируем agent_id
    agent_id = f"agent-{user_id}"
    
    # 2. Формируем LLM config с нашим proxy endpoint
    llm_config = {
        "model": "gpt-4",
        "model_endpoint_type": "openai",
        "model_endpoint": f"{OUR_BACKEND_URL}/api/v1/llm-proxy/{agent_id}/chat/completions",
        "context_window": 8192
    }
    
    # 3. Создаем агента в Letta с этой конфигурацией
    # 4. Сохраняем agent_id в user_profiles
```

#### **5. Переменные окружения**

Добавь новые переменные:
```env
# Наш бекенд URL (для proxy endpoints)
BACKEND_BASE_URL=https://your-backend-url.com

# Глобальный API ключ от Letta (для проверки запросов)
LETTA_GLOBAL_API_KEY=your-global-key-from-letta-env
```

#### **6. Тестирование**

Создай тестовый endpoint для проверки proxy:
```python
@router.get("/{agent_id}/test")
async def test_proxy(agent_id: str):
    """
    Тестовый endpoint для проверки маппинга agent_id → user
    """
    # Вернуть информацию о пользователе и его ключе (без самого ключа)
```

### **Важные детали**

1. **Headers проксирования**: Убедись, что все необходимые headers передаются в LiteLLM (особенно Content-Type и Authorization)

2. **Streaming**: Обязательно реализуй поддержку streaming, так как Letta может использовать это для real-time ответов

3. **Логирование**: Добавь детальное логирование всех запросов для отладки (но не логируй сами ключи!)

4. **Кэширование**: Можно добавить кэширование маппинга agent_id → litellm_key для производительности

5. **Валидация**: Проверяй, что тело запроса от Letta соответствует OpenAI format

6. **Метрики**: Сохраняй информацию о количестве запросов, токенах и стоимости в нашей БД для дополнительной аналитики

### **Результат**

После реализации этого proxy layer:
- Каждый Letta агент будет использовать свой уникальный endpoint
- Запросы будут автоматически проксироваться в LiteLLM с правильным ключом пользователя
- Биллинг будет работать корректно для каждого пользователя
- Система будет полностью функциональна

**Начни с реализации базового proxy endpoint, затем добавь streaming поддержку и обнови логику создания агентов.**