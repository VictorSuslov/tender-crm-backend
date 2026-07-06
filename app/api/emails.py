from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.database import get_db
from app.models.email import Email
from app.schemas.email import EmailRead, EmailList
from app.services.email_service import EmailService


router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.get("/", response_model=EmailList)
async def list_emails(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=15000),
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None, description="Поиск по теме и отправителю"),
    db: AsyncSession = Depends(get_db),
):
    """Получить список писем с пагинацией, фильтрацией и поиском."""
    query = select(Email)
    count_query = select(func.count(Email.id))
    
    # Фильтр по категории
    if category:
        query = query.where(Email.category == category)
        count_query = count_query.where(Email.category == category)
    
    # Поиск по теме и отправителю
    if search:
        search_pattern = f"%{search}%"
        search_filter = or_(
            Email.subject.ilike(search_pattern),
            Email.from_email.ilike(search_pattern),
            Email.from_name.ilike(search_pattern),
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)
    
    # Общее количество
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Сортировка и пагинация
    query = query.order_by(
        desc(Email.email_date),
        desc(Email.received_at)
    )
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(query)
    items = result.scalars().all()
    
    return EmailList(
        items=items,
        total=total,
        page=page,
        per_page=per_page
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