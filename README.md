# AI Chat Platform - Backend

Персонализированная платформа чата с ИИ, которая создает уникальных агентов для каждого пользователя с долгосрочной памятью всех взаимодействий.

## 🚀 Особенности

- **Персональные ИИ агенты** - каждый пользователь получает уникальный агент с памятью
- **Долгосрочная память** - агенты помнят всю историю взаимодействий
- **Управление бюджетом** - контроль расходов на LLM запросы
- **Потоковые ответы** - реальное время через Server-Sent Events
- **Безопасная аутентификация** - JWT токены через Supabase Auth
- **Масштабируемая архитектура** - готова к росту нагрузки

## 🏗️ Архитектура

```
Frontend ↔ FastAPI Backend ↔ Letta (Агенты) + LiteLLM (Биллинг) + Supabase (DB/Auth)
```

### Основные компоненты:
- **FastAPI** - основное API приложение
- **Letta** - статeful агенты с памятью  
- **LiteLLM** - прокси для биллинга LLM запросов
- **Supabase** - аутентификация и база данных

## 📋 Требования

- Python 3.9+
- PostgreSQL (через Supabase)
- Доступ к внешним сервисам: Letta, LiteLLM

## ⚡ Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

```bash
cp .env.example .env
```

Заполните переменные в `.env` файле:

```env
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key

# Letta
LETTA_BASE_URL=https://lettalettalatest-production-4de4.up.railway.app
LETTA_API_TOKEN=  # Оставить пустым для self-hosted

# LiteLLM
LITELLM_BASE_URL=https://litellm-production-1c8b.up.railway.app
LITELLM_MASTER_KEY=your_master_key

# Настройки бюджета пользователей
USER_DEFAULT_BUDGET=10.0  # USD
USER_BUDGET_DURATION=1mo  # 1d, 1w, 1mo, 3mo, 6mo, 1y

# FastAPI
SECRET_KEY=your_secret_key
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 3. Запуск локального сервера

```bash
# Запуск с автоперезагрузкой
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Или через main.py
python -m app.main
```

API будет доступно по адресу: `http://localhost:8000`

Документация API: `http://localhost:8000/docs` (только в development режиме)

## 🐳 Docker

### Сборка и запуск через Docker

```bash
# Сборка образа
docker build -t ai-chat-backend .

# Запуск контейнера
docker run -p 8000:8000 --env-file .env ai-chat-backend
```

### Docker Compose

```bash
# Запуск всех сервисов
docker-compose up -d

# Остановка
docker-compose down
```

## 📚 Документация

- **[API Documentation](API_DOCUMENTATION.md)** - Полная документация по всем endpoint'ам
- **[Architecture](ARCHITECTURE.md)** - Подробное описание архитектуры системы
- **[CLAUDE.md](CLAUDE.md)** - Инструкции для Claude Code разработки

## 🛠️ Основные endpoint'ы

### Аутентификация
```
POST /api/v1/auth/register    # Регистрация пользователя
POST /api/v1/auth/login       # Вход в систему
GET  /api/v1/auth/me          # Текущий пользователь
```

### Чат
```
POST /api/v1/chat/message     # Отправить сообщение (с потоковым ответом)
GET  /api/v1/chat/history     # История сообщений
```

### Пользователь
```
GET  /api/v1/user/profile     # Профиль пользователя
GET  /api/v1/user/usage       # Статистика использования
GET  /api/v1/user/budget      # Информация о бюджете
POST /api/v1/user/budget      # Обновление бюджета
```

### Агент
```
GET  /api/v1/agent/status     # Статус агента
GET  /api/v1/agent/memory     # Память агента
POST /api/v1/agent/memory     # Обновление памяти
POST /api/v1/agent/reset      # Сброс агента
```

## 🔧 Разработка

### Структура проекта

```
backend/
├── app/
│   ├── main.py              # Основное FastAPI приложение
│   ├── config.py            # Конфигурация
│   ├── models/              # Pydantic модели
│   ├── routers/             # API маршруты
│   ├── services/            # Бизнес-логика
│   └── utils/               # Вспомогательные функции
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── README.md
```

### Добавление новых зависимостей

```bash
pip install package_name
pip freeze > requirements.txt
```

### Линтинг и форматирование

```bash
# Black для форматирования
black app/

# isort для импортов
isort app/

# Проверка типов с mypy
mypy app/
```

## 🚀 Деплой

### Railway (Production)

Приложение автоматически деплоится на Railway при push в main ветку.

Production URL: `https://ai-chat-backend-production.up.railway.app`

### Переменные окружения для production

Убедитесь, что все необходимые переменные настроены в Railway:
- Все Supabase ключи
- LiteLLM мастер-ключ  
- Настройки бюджета пользователей
- SECRET_KEY для JWT

## 🧪 Тестирование

### Проверка здоровья API

```bash
curl https://ai-chat-backend-production.up.railway.app/health
```

### Регистрация тестового пользователя

```bash
curl -X POST "https://ai-chat-backend-production.up.railway.app/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'
```

### Отправка сообщения

```bash
# Получить токен после регистрации, затем:
curl -X POST "https://ai-chat-backend-production.up.railway.app/api/v1/chat/message" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content": "Привет! Как дела?"}'
```

## 🔍 Мониторинг

### Логи

```bash
# Локальные логи
tail -f logs/app.log

# Railway логи
railway logs
```

### Health checks

- `GET /health` - здоровье API
- `GET /api/v1/user/health` - здоровье аккаунта пользователя

## ⚠️ Важные замечания

### Безопасность
- Никогда не коммитьте `.env` файл
- Используйте сильные SECRET_KEY в production
- Регулярно обновляйте зависимости

### Производительность  
- Все операции асинхронные
- Потоковые ответы для чата
- Подключение к базе данных через connection pooling

### Биллинг
- Пользователи создаются с лимитом бюджета
- Автоматическое отслеживание расходов через LiteLLM
- Бюджеты сбрасываются автоматически по расписанию

## 🤝 Вклад в проект

1. Fork репозиторий
2. Создайте feature ветку (`git checkout -b feature/AmazingFeature`)
3. Коммитьте изменения (`git commit -m 'Add some AmazingFeature'`)
4. Push в ветку (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

## 📞 Поддержка

При возникновении проблем:

1. Проверьте логи приложения
2. Убедитесь, что все внешние сервисы доступны
3. Проверьте настройки переменных окружения
4. Создайте issue в репозитории с подробным описанием проблемы

## 📄 Лицензия

Этот проект создан для демонстрационных целей.

## 🔗 Полезные ссылки

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Letta Documentation](https://docs.letta.com/)
- [LiteLLM Documentation](https://docs.litellm.ai/)
- [Supabase Documentation](https://supabase.com/docs)