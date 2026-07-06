from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения, загружаются из .env файла."""
    
    # Приложение
    APP_NAME: str = Field(default="Tender CRM")
    APP_ENV: str = Field(default="development")
    DEBUG: bool = Field(default=False)
    
    # PostgreSQL
    DATABASE_URL: str
    
    # Ollama
    OLLAMA_API_URL: str = Field(default="http://localhost:11434/api/generate")
    OLLAMA_MODEL: str = Field(default="qwen2.5:7b")
    
    # IMAP
    IMAP_SERVER: Optional[str] = None
    IMAP_LOGIN: Optional[str] = None
    IMAP_PASSWORD: Optional[str] = None
    
    # Telegram
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None

    # Telegram Proxy
    TELEGRAM_PROXY_URL: Optional[str] = None
    TELEGRAM_PROXY_ENABLED: bool = False
    
    # RAG
    EMBEDDING_MODEL_NAME: str = "jeffh/intfloat-multilingual-e5-large-instruct:q8_0"
    EMBEDDING_DIMENSIONS: int = 1024
    RAG_CHUNK_SIZE: int = 300
    RAG_CHUNK_OVERLAP: int = 50
    RAG_TOP_K: int = 5
    
    # В классе Settings
    IMAP_BATCH_SIZE: int = 100          # Размер пакета для обработки
    IMAP_PAUSE_BETWEEN_BATCHES: int = 5 # Пауза между пакетами (сек)
    IMAP_MAX_EMAILS_PER_RUN: int = 500  # Максимум писем за один запуск
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Глобальный экземпляр настроек
settings = Settings()