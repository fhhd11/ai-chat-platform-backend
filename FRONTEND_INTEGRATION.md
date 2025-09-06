# Frontend Integration Guide

Руководство по интеграции с AI Chat Platform Backend для фронтенд разработчиков.

## 🎯 Обзор интеграции

Этот backend предоставляет REST API с поддержкой потоковых ответов (Server-Sent Events) для создания современного чат-приложения с ИИ агентами.

## 🔐 Аутентификация

### JWT Токены

Backend использует JWT токены от Supabase Auth. После успешной регистрации/авторизации вы получите токены:

```typescript
interface AuthResponse {
  tokens: {
    access_token: string;    // Используется для API запросов
    refresh_token: string;   // Для обновления токена
  };
  user: {
    id: string;
    email: string;
    created_at: string;
  };
}
```

### Использование токенов

Включайте JWT токен в каждый API запрос:

```javascript
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};
```

## 📡 Основные интеграции

### 1. Регистрация и авторизация

```typescript
// Регистрация пользователя
const register = async (email: string, password: string) => {
  const response = await fetch(`${API_BASE}/api/v1/auth/register`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  
  if (!response.ok) {
    throw new Error('Registration failed');
  }
  
  return await response.json();
};

// Авторизация
const login = async (email: string, password: string) => {
  const response = await fetch(`${API_BASE}/api/v1/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ email, password })
  });
  
  return await response.json();
};

// Получение текущего пользователя
const getCurrentUser = async (token: string) => {
  const response = await fetch(`${API_BASE}/api/v1/auth/me`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
};
```

### 2. Чат с потоковыми ответами

```typescript
interface StreamingChatHook {
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => Promise<void>;
  error: string | null;
}

const useChatStream = (token: string): StreamingChatHook => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = async (content: string) => {
    if (!token) return;
    
    setIsStreaming(true);
    setError(null);

    // Добавляем пользовательское сообщение
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    };
    
    setMessages(prev => [...prev, userMessage]);

    try {
      const response = await fetch(`${API_BASE}/api/v1/chat/message`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream'
        },
        body: JSON.stringify({ content })
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      
      let assistantMessage: Message = {
        id: Date.now().toString() + '_assistant',
        role: 'assistant',
        content: '',
        timestamp: new Date().toISOString()
      };
      
      setMessages(prev => [...prev, assistantMessage]);

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                
                if (data.type === 'content_block_delta') {
                  const deltaText = data.delta?.text || '';
                  
                  setMessages(prev => 
                    prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { ...msg, content: msg.content + deltaText }
                        : msg
                    )
                  );
                } else if (data.type === 'message_end') {
                  // Обновляем финальные метрики использования
                  setMessages(prev => 
                    prev.map(msg => 
                      msg.id === assistantMessage.id 
                        ? { ...msg, usage: data.message?.usage }
                        : msg
                    )
                  );
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setIsStreaming(false);
    }
  };

  return {
    messages,
    isStreaming,
    sendMessage,
    error
  };
};
```

### 3. История сообщений

```typescript
interface ChatHistory {
  messages: Message[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    pages: number;
  };
}

const getChatHistory = async (
  token: string, 
  page: number = 1, 
  pageSize: number = 50
): Promise<ChatHistory> => {
  const response = await fetch(
    `${API_BASE}/api/v1/chat/history?page=${page}&page_size=${pageSize}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  
  return await response.json();
};

// React Hook для истории чата
const useChatHistory = (token: string) => {
  const [history, setHistory] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [hasMore, setHasMore] = useState(true);

  const loadHistory = async (page: number = 1) => {
    if (!token) return;
    
    const data = await getChatHistory(token, page);
    
    if (page === 1) {
      setHistory(data.messages);
    } else {
      setHistory(prev => [...prev, ...data.messages]);
    }
    
    setHasMore(data.pagination.page < data.pagination.pages);
    setLoading(false);
  };

  useEffect(() => {
    loadHistory();
  }, [token]);

  return { history, loading, hasMore, loadMore: loadHistory };
};
```

### 4. Профиль пользователя и статистика

```typescript
interface UserStats {
  profile: UserProfile;
  database_usage: {
    total_usage: UsageMetrics;
    today_usage: UsageMetrics;
  };
  billing_usage: {
    total_cost: number;
    total_requests: number;
  };
  budget_info: {
    max_budget: number;
    current_spend: number;
    budget_duration: string;
    budget_remaining: number;
    budget_reset_at: string;
  };
  summary: UsageSummary;
}

const getUserStats = async (token: string): Promise<UserStats> => {
  const response = await fetch(`${API_BASE}/api/v1/user/usage`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
};

// React Hook для статистики пользователя
const useUserStats = (token: string) => {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshStats = async () => {
    if (!token) return;
    
    try {
      const data = await getUserStats(token);
      setStats(data);
    } catch (error) {
      console.error('Failed to load user stats:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshStats();
  }, [token]);

  return { stats, loading, refresh: refreshStats };
};
```

### 5. Управление бюджетом

```typescript
const updateBudget = async (
  token: string,
  maxBudget: number,
  duration: string = '1mo'
) => {
  const response = await fetch(`${API_BASE}/api/v1/user/budget`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      max_budget: maxBudget,
      duration
    })
  });
  
  return await response.json();
};

const getBudgetInfo = async (token: string) => {
  const response = await fetch(`${API_BASE}/api/v1/user/budget`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
};
```

### 6. Управление агентом

```typescript
// Получение информации об агенте
const getAgentStatus = async (token: string) => {
  const response = await fetch(`${API_BASE}/api/v1/agent/status`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  
  return await response.json();
};

// Обновление памяти агента
const updateAgentMemory = async (
  token: string,
  persona: string,
  human: string
) => {
  const response = await fetch(`${API_BASE}/api/v1/agent/memory`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ persona, human })
  });
  
  return await response.json();
};

// Сброс агента
const resetAgent = async (token: string) => {
  const response = await fetch(`${API_BASE}/api/v1/agent/reset`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  
  return await response.json();
};
```

## 🎨 React Components Examples

### ChatInterface Component

```tsx
import React, { useState, useEffect } from 'react';

interface ChatInterfaceProps {
  token: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ token }) => {
  const { messages, isStreaming, sendMessage, error } = useChatStream(token);
  const [inputValue, setInputValue] = useState('');

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() && !isStreaming) {
      await sendMessage(inputValue);
      setInputValue('');
    }
  };

  return (
    <div className="chat-interface">
      <div className="messages-container">
        {messages.map((message) => (
          <div key={message.id} className={`message ${message.role}`}>
            <div className="content">{message.content}</div>
            {message.usage && (
              <div className="usage-info">
                Tokens: {message.usage.total_tokens} | 
                Cost: ${message.usage.estimated_cost?.toFixed(4)}
              </div>
            )}
          </div>
        ))}
        {isStreaming && <div className="typing-indicator">Печатает...</div>}
      </div>

      <form onSubmit={handleSendMessage} className="message-input">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Введите сообщение..."
          disabled={isStreaming}
        />
        <button type="submit" disabled={isStreaming || !inputValue.trim()}>
          Отправить
        </button>
      </form>

      {error && <div className="error">{error}</div>}
    </div>
  );
};
```

### UserDashboard Component

```tsx
const UserDashboard: React.FC<{ token: string }> = ({ token }) => {
  const { stats, loading, refresh } = useUserStats(token);

  if (loading) return <div>Загрузка...</div>;
  if (!stats) return <div>Ошибка загрузки данных</div>;

  return (
    <div className="user-dashboard">
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Общая статистика</h3>
          <p>Сообщений: {stats.summary.total_messages}</p>
          <p>Токенов: {stats.summary.total_tokens}</p>
          <p>Потрачено: ${stats.summary.total_cost.toFixed(2)}</p>
        </div>

        <div className="stat-card">
          <h3>Бюджет</h3>
          <p>Лимит: ${stats.budget_info.max_budget}</p>
          <p>Потрачено: ${stats.budget_info.current_spend}</p>
          <p>Осталось: ${stats.budget_info.budget_remaining}</p>
          <div className="budget-bar">
            <div 
              className="budget-used"
              style={{
                width: `${(stats.budget_info.current_spend / stats.budget_info.max_budget) * 100}%`
              }}
            />
          </div>
        </div>

        <div className="stat-card">
          <h3>Сегодня</h3>
          <p>Сообщений: {stats.summary.today_messages}</p>
          <p>Токенов: {stats.summary.today_tokens}</p>
          <p>Потрачено: ${stats.summary.today_cost.toFixed(2)}</p>
        </div>
      </div>

      <button onClick={refresh}>Обновить статистику</button>
    </div>
  );
};
```

## 🎛️ TypeScript Definitions

```typescript
// Основные типы данных
interface UserProfile {
  id: string;
  email: string;
  name?: string;
  letta_agent_id: string;
  created_at: string;
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  usage?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    estimated_cost?: number;
  };
}

interface UsageMetrics {
  total_messages: number;
  total_tokens: number;
  total_cost: number;
}

interface AgentInfo {
  agent_id: string;
  status: string;
  created_at: string;
  last_updated: string;
  name: string;
  persona: string;
  human: string;
  tools: string[];
}

interface BudgetInfo {
  max_budget: number;
  current_spend: number;
  budget_duration: string;
  budget_remaining: number;
  budget_reset_at: string;
  status: 'active' | 'default_budget';
}

// API Response типы
interface ApiResponse<T = any> {
  status: 'success' | 'error';
  data?: T;
  message?: string;
  error?: string;
}

interface AuthTokens {
  access_token: string;
  refresh_token: string;
}

interface StreamEvent {
  type: 'message_start' | 'content_block_start' | 'content_block_delta' | 'content_block_stop' | 'message_end';
  message?: any;
  delta?: {
    type: string;
    text: string;
  };
  index?: number;
}
```

## 🚨 Обработка ошибок

```typescript
// Глобальный обработчик API ошибок
const handleApiError = (error: any) => {
  if (error.status === 401) {
    // Токен истек или невалидный
    localStorage.removeItem('auth_token');
    window.location.href = '/login';
    return;
  }
  
  if (error.status === 403) {
    // Недостаточно прав или бюджет исчерпан
    console.error('Access denied or budget exceeded');
    return;
  }
  
  if (error.status >= 500) {
    // Серверная ошибка
    console.error('Server error:', error);
    return;
  }
  
  // Другие ошибки
  console.error('API Error:', error);
};

// Обертка для API вызовов с обработкой ошибок
const apiCall = async (url: string, options: RequestInit = {}) => {
  try {
    const response = await fetch(url, options);
    
    if (!response.ok) {
      const errorData = await response.json();
      throw { ...errorData, status: response.status };
    }
    
    return await response.json();
  } catch (error) {
    handleApiError(error);
    throw error;
  }
};
```

## ⚡ Production Tips

### 1. Переменные окружения

```javascript
// .env.local или config
const API_CONFIG = {
  BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || 'https://ai-chat-backend-production.up.railway.app',
  WS_URL: process.env.NEXT_PUBLIC_WS_URL,
  TIMEOUT: 30000
};
```

### 2. Кеширование и оптимизация

```typescript
// Кеширование пользовательских данных
const useUserCache = () => {
  const cacheKey = 'user_data';
  const cacheTimeout = 5 * 60 * 1000; // 5 минут

  const getCachedData = () => {
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      const { data, timestamp } = JSON.parse(cached);
      if (Date.now() - timestamp < cacheTimeout) {
        return data;
      }
    }
    return null;
  };

  const setCachedData = (data: any) => {
    localStorage.setItem(cacheKey, JSON.stringify({
      data,
      timestamp: Date.now()
    }));
  };

  return { getCachedData, setCachedData };
};
```

### 3. Reconnection для потоковых соединений

```typescript
const useReconnectingStream = (token: string) => {
  const maxRetries = 3;
  const retryDelay = 1000;

  const sendMessageWithRetry = async (content: string, retryCount = 0) => {
    try {
      await sendMessage(content);
    } catch (error) {
      if (retryCount < maxRetries) {
        console.log(`Retry ${retryCount + 1}/${maxRetries}`);
        setTimeout(() => {
          sendMessageWithRetry(content, retryCount + 1);
        }, retryDelay * Math.pow(2, retryCount));
      } else {
        throw error;
      }
    }
  };

  return { sendMessageWithRetry };
};
```

Эта документация поможет вам быстро интегрировать фронтенд с AI Chat Platform Backend и создать полнофункциональное чат-приложение с ИИ агентами.