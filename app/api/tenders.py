from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.schemas.email import EmailRead, EmailList
from app.services.email_service import EmailService

from app.database import get_db
from app.schemas.tender import (
    TenderCreate,
    TenderUpdate,
    TenderRead,
    TenderList,
    TenderStatusUpdate,
)
from app.services.tender_service import TenderService


router = APIRouter(prefix="/api/tenders", tags=["tenders"])


@router.get("/", response_model=TenderList)
async def list_tenders(
    status: Optional[str] = Query(None, description="Фильтр по статусу"),
    search: Optional[str] = Query(None, description="Поиск по названию/номеру"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Размер страницы"),
    db: AsyncSession = Depends(get_db),
):
    """Получить список тендеров с фильтрацией и пагинацией."""
    tenders, total = await TenderService.get_tenders(
        db, status=status, page=page, per_page=per_page, search=search
    )
    
    # Дополняем данные количеством связанных писем
    items = []
    for tender in tenders:
        linked_count = await TenderService.get_linked_emails_count(db, tender.id)
        item = TenderRead.model_validate(tender)
        item.linked_emails_count = linked_count
        items.append(item)
    
    return TenderList(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{tender_id}", response_model=TenderRead)
async def get_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить тендер по ID."""
    tender = await TenderService.get_tender_by_id(db, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    linked_count = await TenderService.get_linked_emails_count(db, tender.id)
    result = TenderRead.model_validate(tender)
    result.linked_emails_count = linked_count
    
    return result


@router.post("/", response_model=TenderRead, status_code=201)
async def create_tender(
    tender_data: TenderCreate,
    db: AsyncSession = Depends(get_db),
):
    """Создать новый тендер."""
    # В будущем здесь будет получение user_id из JWT
    tender = await TenderService.create_tender(db, tender_data, created_by=1)
    await db.commit()
    
    result = TenderRead.model_validate(tender)
    result.linked_emails_count = 0
    
    return result


@router.put("/{tender_id}", response_model=TenderRead)
async def update_tender(
    tender_id: int,
    tender_data: TenderUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Обновить тендер."""
    tender = await TenderService.update_tender(db, tender_id, tender_data, user_id=1)
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    await db.commit()
    
    linked_count = await TenderService.get_linked_emails_count(db, tender.id)
    result = TenderRead.model_validate(tender)
    result.linked_emails_count = linked_count
    
    return result


@router.patch("/{tender_id}/status", response_model=TenderRead)
async def update_tender_status(
    tender_id: int,
    status_data: TenderStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Изменить статус тендера."""
    # Валидация статуса
    valid_statuses = ['NEW', 'IN_PROGRESS', 'SUBMITTED', 'WON', 'LOST', 'CANCELLED', 'ARCHIVED']
    if status_data.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Недопустимый статус. Доступные: {', '.join(valid_statuses)}"
        )
    
    tender = await TenderService.update_status(
        db,
        tender_id,
        status_data.status,
        result=status_data.result,
        user_id=1,
        comment=status_data.comment,
    )
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    await db.commit()
    
    linked_count = await TenderService.get_linked_emails_count(db, tender.id)
    result = TenderRead.model_validate(tender)
    result.linked_emails_count = linked_count
    
    return result

@router.get("/{tender_id}/emails", response_model=EmailList)
async def get_tender_emails(
    tender_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Получить все письма, связанные с тендером."""
    # Проверяем существование тендера
    tender = await TenderService.get_tender_by_id(db, tender_id)
    if not tender:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    emails, total = await EmailService.get_tender_emails(
        db, tender_id, page=page, per_page=per_page
    )
    
    items = []
    for email in emails:
        linked_tenders = await EmailService.get_linked_tenders(db, email.id)
        item = EmailRead.model_validate(email)
        item.linked_tenders = linked_tenders
        items.append(item)
    
    return EmailList(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )
    
@router.delete("/{tender_id}", status_code=204)
async def delete_tender(
    tender_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Архивировать тендер (мягкое удаление)."""
    success = await TenderService.delete_tender(db, tender_id, user_id=1)
    if not success:
        raise HTTPException(status_code=404, detail="Тендер не найден")
    
    await db.commit()
    return None