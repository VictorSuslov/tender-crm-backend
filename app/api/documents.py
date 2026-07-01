from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime
import time

from app.database import get_db, async_session
from app.models.document import Document, DocumentChunk
from app.models.email import Email
from app.models.tender import Tender
from app.schemas.document import (
    DocumentCreate,
    DocumentRead,
    DocumentList,
    DocumentIndexResult,
    DocumentFromEmail,
    SearchResult,
    SearchChunk,
)
from app.services.document_service import document_service
from app.services.embedding_service import embedding_service


router = APIRouter(prefix="/api/documents", tags=["documents"])


# ============================================================================
# CRUD операции с документами
# ============================================================================

@router.post("/tenders/{tender_id}", response_model=DocumentRead, status_code=201)
async def create_document(
    tender_id: int,
    data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    """
    Создать новый документ для тендера.
    
    Типы документов:
    - TENDER_APPLICATION — заявка на участие
    - SUPPLEMENT — дополнительное соглашение
    - EMAIL — письмо
    - NOTE — заметка пользователя
    """
    # Проверяем существование тендера
    result = await db.execute(select(Tender).where(Tender.id == tender_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    doc = await document_service.create_document(
        tender_id=tender_id,
        doc_type=data.doc_type,
        title=data.title,
        content=data.content,
        metadata=data.metadata,
    )
    
    return doc


@router.get("/tenders/{tender_id}", response_model=DocumentList)
async def list_documents(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить список всех документов тендера."""
    # Проверяем существование тендера
    result = await db.execute(select(Tender).where(Tender.id == tender_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    documents = await document_service.get_documents_by_tender(tender_id)
    
    return DocumentList(
        items=documents,
        total=len(documents),
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить документ по ID."""
    doc = await document_service.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    return doc


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Удалить документ и все его чанки."""
    success = await document_service.delete_document(document_id)
    if not success:
        raise HTTPException(status_code=404, detail="Документ не найден")


# ============================================================================
# Индексация документов
# ============================================================================

@router.post("/{document_id}/index", response_model=DocumentIndexResult)
async def index_document(
    document_id: int,
    background: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Проиндексировать документ: разбить на чанки и создать эмбеддинги.
    
    ⚠️ Внимание: операция занимает ~1-2 секунды на каждый чанк.
    Для больших документов может потребоваться несколько минут.
    """
    # Проверяем существование документа
    doc = await document_service.get_document_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Документ не найден")
    
    start_time = time.time()
    
    try:
        chunks_count = await document_service.index_document(document_id)
        processing_time = int((time.time() - start_time) * 1000)
        
        # Получаем обновленный документ
        doc = await document_service.get_document_by_id(document_id)
        
        return DocumentIndexResult(
            document_id=document_id,
            chunks_count=chunks_count,
            indexed_at=doc.indexed_at,
            processing_time_ms=processing_time,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при индексации: {str(e)}"
        )


@router.post("/tenders/{tender_id}/index-all")
async def index_all_documents(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Проиндексировать все неиндексированные документы тендера.
    
    Полезно для массовой индексации после загрузки нескольких документов.
    """
    # Проверяем существование тендера
    result = await db.execute(select(Tender).where(Tender.id == tender_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    # Получаем неиндексированные документы
    result = await db.execute(
        select(Document).where(
            Document.tender_id == tender_id,
            Document.is_indexed == False
        )
    )
    documents = result.scalars().all()
    
    if not documents:
        return {
            "status": "ok",
            "message": "Нет документов для индексации",
            "indexed_count": 0,
            "total_chunks": 0,
        }
    
    total_chunks = 0
    indexed_ids = []
    
    for doc in documents:
        try:
            chunks_count = await document_service.index_document(doc.id)
            total_chunks += chunks_count
            indexed_ids.append(doc.id)
        except Exception as e:
            print(f"⚠ Ошибка индексации документа {doc.id}: {e}")
    
    return {
        "status": "ok",
        "message": f"Проиндексировано {len(indexed_ids)} документов",
        "indexed_count": len(indexed_ids),
        "indexed_ids": indexed_ids,
        "total_chunks": total_chunks,
    }


# ============================================================================
# Создание документов из писем
# ============================================================================

@router.post("/from-email/{email_id}", response_model=DocumentRead, status_code=201)
async def create_document_from_email(
    email_id: int,
    tender_id: int = Query(..., description="ID тендера для привязки документа"),
    data: DocumentFromEmail = DocumentFromEmail(),
    db: AsyncSession = Depends(get_db),
):
    """
    Создать документ из письма.
    
    Создает документ типа EMAIL с содержимым письма и (опционально) 
    текстом из вложений.
    """
    # Получаем письмо
    result = await db.execute(select(Email).where(Email.id == email_id))
    email = result.scalar_one_or_none()
    if not email:
        raise HTTPException(status_code=404, detail="Письмо не найдено")
    
    # Проверяем существование тендера
    result = await db.execute(select(Tender).where(Tender.id == tender_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    # Формируем содержимое документа
    content_parts = []
    
    # Метаданные письма
    content_parts.append(f"Тема: {email.subject or '(без темы)'}")
    content_parts.append(f"От: {email.from_name or email.from_email}")
    content_parts.append(f"Дата: {email.email_date}")
    content_parts.append("")
    
    # Тело письма
    if email.body_text:
        content_parts.append("=== ТЕКСТ ПИСЬМА ===")
        content_parts.append(email.body_text)
        content_parts.append("")
    
    # Резюме LLM
    if email.summary:
        content_parts.append("=== РЕЗЮМЕ ===")
        content_parts.append(email.summary)
        content_parts.append("")
    
    # Тендерные данные
    if email.tender_details:
        content_parts.append("=== ТЕНДЕРНЫЕ ДАННЫЕ ===")
        for key, value in email.tender_details.items():
            if value:
                content_parts.append(f"{key}: {value}")
        content_parts.append("")
    
    # Текст из вложений
    if data.include_attachments_text and email.attachments_info:
        content_parts.append("=== ВЛОЖЕНИЯ ===")
        for att in email.attachments_info:
            content_parts.append(f"- {att.get('filename', 'без имени')} ({att.get('size_bytes', 0)} байт)")
    
    content = "\n".join(content_parts)
    
    # Создаем документ
    doc = await document_service.create_document(
        tender_id=tender_id,
        email_id=email_id,
        doc_type="EMAIL",
        title=email.subject or f"Письмо #{email_id}",
        content=content,
        metadata={
            "from_email": email.from_email,
            "from_name": email.from_name,
            "email_date": email.email_date.isoformat() if email.email_date else None,
            "category": email.category,
        },
    )
    
    return doc


# ============================================================================
# Семантический поиск
# ============================================================================

@router.post("/search", response_model=SearchResult)
async def search_documents(
    query: str = Query(..., min_length=3, description="Поисковый запрос"),
    tender_id: Optional[int] = Query(None, description="ID тендера для фильтрации"),
    top_k: int = Query(5, ge=1, le=20, description="Количество результатов"),
    db: AsyncSession = Depends(get_db),
):
    """
    Семантический поиск по документам.
    
    Использует векторные эмбеддинги для поиска релевантных фрагментов.
    Если указан tender_id — поиск только в документах этого тендера.
    """
    # Если указан tender_id — проверяем его существование
    if tender_id:
        result = await db.execute(select(Tender).where(Tender.id == tender_id))
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Тендер не найден")
    
    start_time = time.time()
    
    try:
        chunks = await document_service.search(
            query=query,
            tender_id=tender_id,
            top_k=top_k,
        )
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return SearchResult(
            query=query,
            tender_id=tender_id,
            chunks=[SearchChunk(**chunk) for chunk in chunks],
            total_found=len(chunks),
            processing_time_ms=processing_time,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при поиске: {str(e)}"
        )


# ============================================================================
# Статистика
# ============================================================================

@router.get("/statistics/overview")
async def get_documents_statistics(db: AsyncSession = Depends(get_db)):
    """Получить общую статистику по документам."""
    # Всего документов
    total_result = await db.execute(select(func.count(Document.id)))
    total = total_result.scalar()
    
    # По типам
    type_result = await db.execute(
        select(Document.doc_type, func.count(Document.id))
        .group_by(Document.doc_type)
    )
    by_type = {row[0]: row[1] for row in type_result.all()}
    
    # Индексированные / неиндексированные
    indexed_result = await db.execute(
        select(func.count(Document.id)).where(Document.is_indexed == True)
    )
    indexed = indexed_result.scalar()
    
    # Всего чанков
    chunks_result = await db.execute(select(func.count(DocumentChunk.id)))
    total_chunks = chunks_result.scalar()
    
    # Чанков по тендерам
    chunks_by_tender_result = await db.execute(
        select(DocumentChunk.tender_id, func.count(DocumentChunk.id))
        .group_by(DocumentChunk.tender_id)
    )
    chunks_by_tender = {row[0]: row[1] for row in chunks_by_tender_result.all()}
    
    return {
        "total_documents": total,
        "indexed_documents": indexed,
        "not_indexed_documents": total - indexed,
        "total_chunks": total_chunks,
        "by_type": by_type,
        "chunks_by_tender": chunks_by_tender,
    }