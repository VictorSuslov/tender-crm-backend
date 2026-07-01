from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.rag_query import RagQuery
from app.models.tender import Tender
from app.schemas.document import (
    RagQueryRequest,
    RagQueryResponse,
    RagHistoryItem,
    RagHistoryList,
    SearchChunk,
)
from app.services.rag_service import rag_service


router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/query", response_model=RagQueryResponse)
async def query_rag(
    data: RagQueryRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Задать вопрос RAG-системе.
    
    Система найдет релевантные фрагменты документации и сгенерирует
    ответ на основе найденной информации.
    
    Если указан tender_id — поиск только в документах этого тендера.
    Если tender_id не указан — поиск по всем тендерам.
    """
    # Если указан tender_id — проверяем его существование
    if data.tender_id:
        result = await db.execute(
            select(Tender).where(Tender.id == data.tender_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Тендер не найден")
    
    try:
        result = await rag_service.query(
            question=data.question,
            tender_id=data.tender_id,
            top_k=data.top_k,
        )
        
        # Проверяем, есть ли ошибка
        if "error" in result:
            raise HTTPException(
                status_code=500,
                detail=result["error"]
            )
        
        return RagQueryResponse(
            answer=result["answer"],
            sources=[SearchChunk(**chunk) for chunk in result["sources"]],
            processing_time_ms=result["processing_time_ms"],
            tender_id=data.tender_id,
            question=data.question,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке запроса: {str(e)}"
        )


@router.get("/history", response_model=RagHistoryList)
async def get_rag_history(
    tender_id: Optional[int] = Query(None, description="Фильтр по тендеру"),
    limit: int = Query(20, ge=1, le=100, description="Количество записей"),
    db: AsyncSession = Depends(get_db),
):
    """
    Получить историю RAG-запросов.
    
    Возвращает последние запросы с ответами и метаданными.
    """
    query = select(RagQuery)
    
    if tender_id:
        query = query.where(RagQuery.tender_id == tender_id)
    
    query = query.order_by(desc(RagQuery.created_at)).limit(limit)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    # Подсчет общего количества
    count_query = select(func.count(RagQuery.id))
    if tender_id:
        count_query = count_query.where(RagQuery.tender_id == tender_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    return RagHistoryList(
        items=items,
        total=total,
    )


@router.get("/history/{query_id}", response_model=RagHistoryItem)
async def get_rag_query(
    query_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить конкретный RAG-запрос по ID."""
    result = await db.execute(
        select(RagQuery).where(RagQuery.id == query_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    
    return item


@router.delete("/history/{query_id}", status_code=204)
async def delete_rag_query(
    query_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Удалить запись из истории запросов."""
    result = await db.execute(
        select(RagQuery).where(RagQuery.id == query_id)
    )
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=404, detail="Запрос не найден")
    
    await db.delete(item)
    await db.commit()


@router.get("/statistics")
async def get_rag_statistics(db: AsyncSession = Depends(get_db)):
    """Получить статистику использования RAG."""
    # Всего запросов
    total_result = await db.execute(select(func.count(RagQuery.id)))
    total = total_result.scalar()
    
    # Среднее время обработки
    avg_time_result = await db.execute(
        select(func.avg(RagQuery.processing_time_ms))
        .where(RagQuery.processing_time_ms.isnot(None))
    )
    avg_time = avg_time_result.scalar() or 0
    
    # Запросов по тендерам
    by_tender_result = await db.execute(
        select(RagQuery.tender_id, func.count(RagQuery.id))
        .where(RagQuery.tender_id.isnot(None))
        .group_by(RagQuery.tender_id)
    )
    by_tender = {row[0]: row[1] for row in by_tender_result.all()}
    
    # Популярные вопросы (топ-10 по количеству повторений)
    popular_result = await db.execute(
        select(RagQuery.query, func.count(RagQuery.id).label('count'))
        .group_by(RagQuery.query)
        .order_by(desc('count'))
        .limit(10)
    )
    popular_queries = [
        {"query": row[0], "count": row[1]} 
        for row in popular_result.all()
    ]
    
    return {
        "total_queries": total,
        "average_processing_time_ms": int(avg_time),
        "queries_by_tender": by_tender,
        "popular_queries": popular_queries,
    }