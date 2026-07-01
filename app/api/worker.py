from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.services.email_processor import EmailProcessor


router = APIRouter(prefix="/api/worker", tags=["worker"])


@router.post("/process")
async def process_emails(
    limit: int = Query(50, ge=1, le=200, description="Количество писем для обработки"),
    db: AsyncSession = Depends(get_db),
):
    """
    Запустить обработку новых писем.
    
    ⚠️ Внимание: операция занимает 2-5 минут в зависимости от количества писем.
    Возвращает статистику обработки после завершения.
    """
    try:
        processor = EmailProcessor()
        stats = await processor.process_new_emails(limit=limit)
        
        return {
            "status": "completed",
            "message": "Обработка завершена",
            "stats": stats,
            "summary": (
                f"Получено: {stats['fetched']}, "
                f"Новых: {stats['new']}, "
                f"Проанализировано: {stats['analyzed']}, "
                f"Связано: {stats['linked']}"
            )
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке писем: {str(e)}"
        )


@router.get("/status")
async def get_worker_status(db: AsyncSession = Depends(get_db)):
    """
    Получить статус воркера обработки писем.
    
    Возвращает информацию о последней обработке и текущем состоянии.
    """
    from sqlalchemy import select, func
    from app.models.email import Email
    from datetime import datetime, timedelta
    
    # Статистика по письмам
    total_result = await db.execute(select(func.count(Email.id)))
    total_emails = total_result.scalar()
    
    # Письма за последние 24 часа
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_result = await db.execute(
        select(func.count(Email.id)).where(Email.received_at >= yesterday)
    )
    recent_emails = recent_result.scalar()
    
    # Письма по категориям
    category_result = await db.execute(
        select(Email.category, func.count(Email.id))
        .group_by(Email.category)
    )
    by_category = {row[0]: row[1] for row in category_result.all()}
    
    # Последняя обработка
    last_processed_result = await db.execute(
        select(func.max(Email.processed_at))
    )
    last_processed = last_processed_result.scalar()
    
    return {
        "status": "running",
        "total_emails": total_emails,
        "emails_last_24h": recent_emails,
        "by_category": by_category,
        "last_processed_at": last_processed.isoformat() if last_processed else None,
        "imap_check_interval_minutes": 5,
    }