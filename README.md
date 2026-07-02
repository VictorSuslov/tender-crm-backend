# Tender CRM Backend

Бэкенд системы автоматизированной обработки тендерной документации на основе локальной LLM.

## 🚀 Возможности

### Обработка электронной почты
- Автоматический сбор писем через IMAP (Yandex, Gmail и др.)
- Настраиваемый интервал проверки (по умолчанию 5 минут)
- Фильтрация новых писем по UID — обрабатываются только непрочитанные
- Ручной запуск обработки через API
- Полная обработка ящика (за месяц, 3 месяца, год, весь ящик)

### LLM-анализ
- Классификация писем: TENDER, SPAM, GENERAL, EMPTY
- Извлечение резюме на русском языке
- Извлечение тендерных данных:
  - Название закупки
  - НМЦК (начальная максимальная цена контракта)
  - Срок подачи заявок
  - Номер извещения
- Локальная LLM **Qwen 2.5 7B** через Ollama — данные не покидают сервер

### Парсинг вложений
- PDF (через `pypdf`)
- DOCX (через `python-docx`)
- XLSX / XLS (через `openpyxl` / `xlrd`)
- ZIP (рекурсивное извлечение)
- Автоматическое извлечение текста и передача в LLM

### RAG-система (Retrieval-Augmented Generation)
- Векторное хранилище на базе **pgvector** (PostgreSQL)
- Модель эмбеддингов: **intfloat/multilingual-e5-large** (1024 dims)
- Семантический поиск по документации тендеров
- Генерация ответов с указанием источников
- Фильтрация по тендеру или глобальный поиск
- История запросов с метаданными

### REST API
- Полный набор эндпоинтов для десктоп-клиента
- Swagger-документация (автогенерируемая)
- Асинхронная обработка запросов
- Валидация через Pydantic

### Уведомления
- Telegram-бот для уведомлений о новых тендерных письмах
- Настраиваемые каналы уведомлений
- Поддержка прокси для Telegram

## 🛠 Технологии

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.14 |
| Фреймворк | FastAPI |
| ORM | SQLAlchemy 2.0 (async) |
| СУБД | PostgreSQL 16 + pgvector |
| LLM | Qwen 2.5 7B (Ollama) |
| Эмбеддинги | intfloat/multilingual-e5-large (1024 dims) |
| IMAP | imap_tools |
| Планировщик | APScheduler |
| Парсинг | pypdf, python-docx, openpyxl, xlrd |
| Валидация | Pydantic v2 |
| HTTP-клиент | httpx (async) |

## 📋 Требования

- **Python 3.11+**
- **PostgreSQL 16** с расширением pgvector (см. [tender-crm-database](https://github.com/ВАШ_ЛОГИН/tender-crm-database))
- **Ollama** с моделями:
  - `qwen2.5:7b` — для анализа писем и генерации ответов
  - `jeffh/intfloat-multilingual-e5-large-instruct:q8_0` — для эмбеддингов

## 🚀 Установка

### 1. Клонирование репозитория

    git clone https://github.com/ВАШ_ЛОГИН/tender-crm-backend.git
    cd tender-crm-backend

### 2. Создание виртуального окружения

    python -m venv venv
    venv\Scripts\activate        # Windows
    # source venv/bin/activate   # Linux/Mac

### 3. Установка зависимостей

    pip install -r requirements.txt

### 4. Настройка переменных окружения

    cp .env.example .env

Отредактируйте `.env` и укажите реальные значения:

    # Database
    POSTGRES_USER=tender_user
    POSTGRES_PASSWORD=your_secure_password
    POSTGRES_DB=tender_crm
    POSTGRES_HOST=localhost
    POSTGRES_PORT=5432

    # IMAP
    IMAP_SERVER=imap.yandex.ru
    IMAP_LOGIN=your_email@yandex.ru
    IMAP_PASSWORD=your_app_password
    IMAP_FOLDER=INBOX

    # Ollama
    OLLAMA_API_URL=http://localhost:11434/api/generate
    OLLAMA_MODEL=qwen2.5:7b

    # RAG
    EMBEDDING_MODEL_NAME=jeffh/intfloat-multilingual-e5-large-instruct:q8_0
    EMBEDDING_DIMENSIONS=1024
    RAG_CHUNK_SIZE=500
    RAG_CHUNK_OVERLAP=50
    RAG_TOP_K=5

    # Telegram (опционально)
    TELEGRAM_BOT_TOKEN=
    TELEGRAM_CHAT_ID=
    TELEGRAM_PROXY_URL=
    TELEGRAM_PROXY_ENABLED=false

### 5. Установка моделей Ollama

    ollama pull qwen2.5:7b
    ollama pull jeffh/intfloat-multilingual-e5-large-instruct:q8_0

### 6. Запуск базы данных

См. [tender-crm-database](https://github.com/ВАШ_ЛОГИН/tender-crm-database) для инструкций.

### 7. Запуск приложения

    python -m app.main

Приложение будет доступно по адресу:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 📁 Структура проекта

    tender-crm-backend/
    ├── app/
    │   ├── __init__.py
    │   ├── main.py                 # Точка входа, FastAPI app
    │   ├── config.py               # Конфигурация (Pydantic Settings)
    │   ├── database.py             # Подключение к PostgreSQL
    │   │
    │   ├── models/                 # SQLAlchemy модели
    │   │   ├── user.py
    │   │   ├── tender.py
    │   │   ├── email.py
    │   │   ├── document.py         # Документы для RAG
    │   │   ├── rag_query.py        # История RAG-запросов
    │   │   └── ...
    │   │
    │   ├── schemas/                # Pydantic схемы (DTO)
    │   │   ├── tender.py
    │   │   ├── email.py
    │   │   ├── document.py
    │   │   └── ...
    │   │
    │   ├── api/                    # REST API эндпоинты
    │   │   ├── tenders.py          # CRUD тендеров
    │   │   ├── emails.py           # Работа с письмами
    │   │   ├── documents.py        # Управление документами
    │   │   ├── rag.py              # RAG-запросы и история
    │   │   └── worker.py           # Обработка почты
    │   │
    │   └── services/               # Бизнес-логика
    │       ├── imap_service.py     # Работа с IMAP
    │       ├── email_processor.py  # Обработка писем
    │       ├── llm_analyzer.py     # Анализ через LLM
    │       ├── embedding_service.py # Получение эмбеддингов
    │       ├── document_service.py # Управление документами
    │       └── rag_service.py      # RAG-поиск и генерация
    │
    ├── requirements.txt            # Зависимости Python
    ├── .env.example                # Шаблон переменных окружения
    ├── .env                        # Реальные значения (в .gitignore)
    ├── test_*.py                   # Тестовые скрипты
    └── README.md                   # Этот файл

## 📡 API Endpoints

### Тендеры

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/tenders/` | Список тендеров с пагинацией |
| POST | `/api/tenders/` | Создать тендер |
| GET | `/api/tenders/{id}` | Получить тендер по ID |
| PUT | `/api/tenders/{id}` | Обновить тендер |
| DELETE | `/api/tenders/{id}` | Удалить тендер |

### Письма

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| GET | `/api/emails/` | Список писем с фильтрами |
| GET | `/api/emails/{id}` | Получить письмо по ID |
| POST | `/api/emails/{id}/link` | Связать письмо с тендером |

### Документы

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/documents/tenders/{id}` | Создать документ для тендера |
| GET | `/api/documents/tenders/{id}` | Список документов тендера |
| GET | `/api/documents/{id}` | Получить документ |
| DELETE | `/api/documents/{id}` | Удалить документ |
| POST | `/api/documents/{id}/index` | Индексировать документ (RAG) |
| POST | `/api/documents/from-email/{id}` | Создать документ из письма |
| POST | `/api/documents/search` | Семантический поиск |

### RAG

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/rag/query` | Задать вопрос RAG-системе |
| GET | `/api/rag/history` | История запросов |
| GET | `/api/rag/statistics` | Статистика использования |

### Воркер

| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| POST | `/api/worker/process` | Обработать новые письма |
| POST | `/api/worker/process-all` | Обработать весь ящик |
| GET | `/api/worker/status` | Статус воркера |

### Примеры запросов

#### Создать тендер

    POST /api/tenders/
    {
      "purchase_name": "Реконструкция автодороги",
      "customer_name": "МКУ УКС",
      "nmck": 64833943.20,
      "status": "NEW"
    }

#### RAG-запрос

    POST /api/rag/query
    {
      "question": "Какая НМЦК контракта?",
      "tender_id": 5,
      "top_k": 5
    }

Ответ:

    {
      "answer": "Сумма контракта составляет 64 833 943,20 руб.",
      "sources": [...],
      "processing_time_ms": 4761
    }

#### Семантический поиск

    POST /api/documents/search?query=сроки%20выполнения&tender_id=5&top_k=3

## 🔧 Конфигурация

Все настройки через переменные окружения в `.env`. Ключевые параметры:

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `POSTGRES_HOST` | Хост PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Порт PostgreSQL | `5432` |
| `IMAP_SERVER` | IMAP-сервер | `imap.yandex.ru` |
| `OLLAMA_API_URL` | URL Ollama API | `http://localhost:11434/api/generate` |
| `OLLAMA_MODEL` | Модель LLM | `qwen2.5:7b` |
| `EMBEDDING_MODEL_NAME` | Модель эмбеддингов | `jeffh/intfloat-multilingual-e5-large-instruct:q8_0` |
| `EMBEDDING_DIMENSIONS` | Размерность эмбеддинга | `1024` |
| `RAG_CHUNK_SIZE` | Размер чанка (символы) | `500` |
| `RAG_CHUNK_OVERLAP` | Перекрытие чанков | `50` |
| `RAG_TOP_K` | Количество источников | `5` |

## 🧪 Тестирование

В проекте есть набор тестовых скриптов:

    # Тест модели эмбеддингов
    python test_embedding.py

    # Сравнение моделей эмбеддингов
    python test_embedding_compare.py

    # Тест RAG-системы (прямой вызов сервисов)
    python test_rag.py

    # Тест RAG API (через HTTP)
    python test_rag_api.py

    # Обработка почтового ящика
    python test_process_all.py

## 🏗 Архитектура

### Обработка писем

    IMAP Server
         │
         ▼
    IMAP Service (imap_tools)
         │
         ▼
    Email Processor
         │
         ├──▶ LLM Analyzer (Qwen 2.5 7B)
         │         │
         │         └──▶ Категория, резюме, тендерные данные
         │
         ├──▶ Attachment Parser
         │         │
         │         └──▶ Текст из PDF/DOCX/XLSX/ZIP
         │
         └──▶ PostgreSQL
                   │
                   └──▶ tenders, emails, email_tender_links

### RAG-система

    Пользователь (вопрос)
         │
         ▼
    RAG Service
         │
         ├──▶ Embedding Service (Ollama)
         │         │
         │         └──▶ Вектор запроса (1024 dims)
         │
         ├──▶ Document Service
         │         │
         │         └──▶ pgvector поиск → релевантные чанки
         │
         └──▶ LLM Analyzer
                   │
                   └──▶ Ответ с источниками

### Асинхронная обработка

Все операции с БД и LLM выполняются асинхронно:
- `asyncpg` — асинхронный драйвер PostgreSQL
- `httpx.AsyncClient` — асинхронные HTTP-запросы к Ollama
- `APScheduler` — фоновая обработка почты

## 📊 Производительность

| Операция | Время |
|----------|-------|
| Обработка одного письма (без вложений) | ~3 сек |
| Обработка письма с PDF-вложением | ~10 сек |
| Индексация документа (10 чанков) | ~15 сек |
| Семантический поиск | ~0.7 сек |
| RAG-запрос (поиск + генерация) | ~5 сек |
| Обработка 50 писем | ~3-5 мин |

## 🐛 Отладка

### Логи

Приложение выводит подробные логи в консоль:
- SQL-запросы SQLAlchemy
- HTTP-запросы к Ollama
- Прогресс обработки писем
- Ошибки и исключения

### Распространённые проблемы

**Проблема**: "Connection refused" к PostgreSQL
**Решение**: убедитесь, что контейнер БД запущен (`docker compose ps`)

**Проблема**: "Model not found" в Ollama
**Решение**: установите модели (`ollama pull qwen2.5:7b`)

**Проблема**: "IMAP authentication failed"
**Решение**: проверьте логин/пароль в `.env`, для Yandex используйте пароль приложения

**Проблема**: RAG возвращает нерелевантные ответы
**Решение**: убедитесь, что документы проиндексированы (`is_indexed = true`)

## 🔗 Связанные проекты

- [Database](https://github.com/VictorSuslov/tender-crm-database) — PostgreSQL + pgvector
- [Desktop](https://github.com/VictorSuslov/tender-crm-desktop) — Qt 6 / C++ клиент

## 📄 Лицензия

MIT