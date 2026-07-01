# Tender CRM Backend

Бэкенд системы автоматизированной обработки тендерной документации.

## 🚀 Возможности

- **IMAP-обработчик** — автоматический сбор писем с почтового ящика
- **LLM-анализ** — классификация писем через локальную LLM (Qwen 2.5 7B)
- **Парсинг вложений** — извлечение текста из PDF, DOCX, XLSX, ZIP
- **RAG-система** — семантический поиск с использованием pgvector
- **REST API** — полный набор эндпоинтов для десктоп-клиента

## 🛠 Технологии

| Компонент | Технология |
|-----------|------------|
| Язык | Python 3.14 |
| Фреймворк | FastAPI |
| LLM | Qwen 2.5 7B (Ollama) |
| Эмбеддинги | intfloat/multilingual-e5-large |
| СУБД | PostgreSQL 16 + pgvector |
| ORM | SQLAlchemy 2.0 (async) |

## 📦 Установка

```bash
# Клонирование репозитория
git clone https://github.com/ВАШ_ЛОГИН/tender-crm-backend.git
cd tender-crm-backend

# Создание виртуального окружения
python -m venv venv
venv\Scripts\activate

# Установка зависимостей
pip install -r requirements.txt

# Настройка .env (скопируйте из .env.example)
cp .env.example .env

# Запуск
python -m app.main

📡 API Endpoints
POST /api/tenders/ — создание тендера
POST /api/emails/process — обработка писем
POST /api/rag/query — RAG-запрос
GET /api/documents/statistics/overview — статистика
Документация Swagger: http://localhost:8000/docs