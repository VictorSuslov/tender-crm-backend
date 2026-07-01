from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.schemas.email import (
    EmailRead,
    EmailList,
    EmailLinkCreate,
)
from app.services.email_service import EmailService


router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.get("/", response_model=EmailList)
async def list_emails(
    category: Optional[str] = Query(None, description="Фильтр по категории (TENDER, SPAM, GENERAL, EMPTY)"),
    search: Optional[str] = Query(None, description="Поиск по теме, отправителю, резюме"),
    is_important: Optional[bool] = Query(None, description="Фильтр по важности"),
    has_attachments: Optional[bool] = Query(None, description="Фильтр по наличию вложений"),
    processing_status: Optional[str] = Query(None, description="Статус обработки"),
    page: int = Query(1, ge=1, description="Номер страницы"),
    per_page: int = Query(20, ge=1, le=100, description="Размер страницы"),
    db: AsyncSession = Depends(get_db),
):
    """Получить список писем с фильтрацией и пагинацией."""
    emails, total = await EmailService.get_emails(
        db,
        category=category,
        search=search,
        is_important=is_important,
        has_attachments=has_attachments,
        processing_status=processing_status,
        page=page,
        per_page=per_page,
    )
    
    # Дополняем данные связями с тендерами
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


@router.get("/statistics")
async def get_email_statistics(db: AsyncSession = Depends(get_db)):
    """Получить статистику по письмам."""
    return await EmailService.get_statistics(db)


@router.get("/unlinked", response_model=EmailList)
async def get_unlinked_tender_emails(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Получить тендерные письма без связи с тендерами."""
    emails, total = await EmailService.get_unlinked_tender_emails(
        db, page=page, per_page=per_page
    )
    
    items = [EmailRead.model_validate(e) for e in emails]
    
    return EmailList(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/{email_id}", response_model=EmailRead)
async def get_email(
    email_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить детали письма по ID."""
    email = await EmailService.get_email_by_id(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Письмо не найдено")
    
    linked_tenders = await EmailService.get_linked_tenders(db, email.id)
    result = EmailRead.model_validate(email)
    result.linked_tenders = linked_tenders
    
    return result


@router.post("/{email_id}/link/{tender_id}")
async def link_email_to_tender(
    email_id: int,
    tender_id: int,
    link_type: str = Query(default="MANUAL", description="Тип связи"),
    db: AsyncSession = Depends(get_db),
):
    """Связать письмо с тендером вручную."""
    success = await EmailService.link_email_to_tender(
        db, email_id, tender_id, link_type
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Не удалось создать связь. Проверьте, что письмо и тендер существуют."
        )
    
    await db.commit()
    
    return {
        "status": "ok",
        "message": f"Письмо {email_id} связано с тендером {tender_id}",
        "link_type": link_type,
    }


@router.delete("/{email_id}/link/{tender_id}")
async def unlink_email_from_tender(
    email_id: int,
    tender_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Удалить связь письма с тендером."""
    success = await EmailService.unlink_email_from_tender(db, email_id, tender_id)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Связь не найдена"
        )
    
    await db.commit()
    
    return {
        "status": "ok",
        "message": f"Связь между письмом {email_id} и тендером {tender_id} удалена",
    }


@router.patch("/{email_id}/important")
async def mark_as_important(
    email_id: int,
    is_important: bool = Query(..., description="Отметить как важное"),
    db: AsyncSession = Depends(get_db),
):
    """Отметить письмо как важное/неважное."""
    email = await EmailService.mark_as_important(db, email_id, is_important)
    
    if not email:
        raise HTTPException(status_code=404, detail="Письмо не найдено")
    
    await db.commit()
    
    return {
        "status": "ok",
        "email_id": email_id,
        "is_important": is_important,
    }