from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import test_connection
from app.api.tenders import router as tenders_router
from app.api.worker import router as worker_router
from app.workers.imap_worker import imap_worker
from app.api.emails import router as emails_router
from app.api.documents import router as documents_router
from app.api.rag import router as rag_router
from app.api.documents_upload import router as documents_upload_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Действия при запуске и остановке приложения."""
    # При запуске
    print(f"🚀 Запуск {settings.APP_NAME}...")
    print(f"📊 Окружение: {settings.APP_ENV}")
    
    # Проверяем подключение к БД
    db_ok = await test_connection()
    if not db_ok:
        print("⚠ Приложение запущено, но БД недоступна!")
    
    # Запускаем фоновый воркер (теперь это async метод)
    if db_ok:
        await imap_worker.start()
    
    yield
    
    # При остановке
    print("👋 Остановка приложения...")
    imap_worker.stop()


app = FastAPI(
    title=settings.APP_NAME,
    description="CRM-система для управления тендерами",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(tenders_router)
app.include_router(worker_router)
app.include_router(emails_router)
app.include_router(documents_router)
app.include_router(rag_router)
app.include_router(documents_upload_router)

@app.get("/")
async def root():
    return {
        "service": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    db_ok = await test_connection()
    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )