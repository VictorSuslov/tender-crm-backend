from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.database import get_db
from app.models.email import Email
from app.models.tender import Tender
from app.models.email_tender_link import EmailTenderLink
from app.services.email_service import EmailService

router = APIRouter(prefix="/api/emails", tags=["emails"])


@router.get("/")
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
    emails = result.scalars().all()
    
    # Получаем привязки для всех писем одним запросом
    email_ids = [e.id for e in emails]
    
    links_by_email = {}
    if email_ids:
        links_result = await db.execute(
            select(
                EmailTenderLink.email_id,
                EmailTenderLink.tender_id,
                EmailTenderLink.link_type,
                Tender.purchase_name
            )
            .join(Tender, EmailTenderLink.tender_id == Tender.id)
            .where(EmailTenderLink.email_id.in_(email_ids))
        )
        
        for row in links_result.all():
            email_id = row[0]
            if email_id not in links_by_email:
                links_by_email[email_id] = []
            links_by_email[email_id].append({
                "tender_id": row[1],
                "link_type": row[2],
                "tender_name": row[3]
            })
    
    # Формируем ответ
    items = []
    for email in emails:
        items.append({
            "id": email.id,
            "uid": email.uid,
            "folder": email.folder,
            "from_email": email.from_email,
            "from_name": email.from_name,
            "to_emails": email.to_emails,
            "subject": email.subject,
            "body_text": email.body_text,
            "body_html": email.body_html,
            "email_date": email.email_date.isoformat() if email.email_date else None,
            "received_at": email.received_at.isoformat() if email.received_at else None,
            "category": email.category,
            "summary": email.summary,
            "llm_model_used": email.llm_model_used,
            "tender_details": email.tender_details,
            "attachments_info": email.attachments_info,
            "processing_status": email.processing_status,
            "is_important": email.is_important,
            "is_notified": email.is_notified,
            "linked_tenders": links_by_email.get(email.id, [])
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/statistics")
async def get_email_statistics(db: AsyncSession = Depends(get_db)):
    """Получить статистику по письмам."""
    return await EmailService.get_statistics(db)


@router.get("/unlinked")
async def get_unlinked_tender_emails(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Получить тендерные письма без связи с тендерами."""
    emails, total = await EmailService.get_unlinked_tender_emails(
        db, page=page, per_page=per_page
    )
    
    items = []
    for email in emails:
        items.append({
            "id": email.id,
            "uid": email.uid,
            "folder": email.folder,
            "from_email": email.from_email,
            "from_name": email.from_name,
            "subject": email.subject,
            "category": email.category,
            "summary": email.summary,
            "email_date": email.email_date.isoformat() if email.email_date else None,
            "is_important": email.is_important,
            "linked_tenders": []
        })
    
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page
    }


@router.get("/{email_id}")
async def get_email(
    email_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Получить детали письма по ID."""
    email = await EmailService.get_email_by_id(db, email_id)
    if not email:
        raise HTTPException(status_code=404, detail="Письмо не найдено")
    
    linked_tenders = await EmailService.get_linked_tenders(db, email.id)
    
    return {
        "id": email.id,
        "uid": email.uid,
        "folder": email.folder,
        "from_email": email.from_email,
        "from_name": email.from_name,
        "to_emails": email.to_emails,
        "subject": email.subject,
        "body_text": email.body_text,
        "body_html": email.body_html,
        "email_date": email.email_date.isoformat() if email.email_date else None,
        "received_at": email.received_at.isoformat() if email.received_at else None,
        "category": email.category,
        "summary": email.summary,
        "llm_model_used": email.llm_model_used,
        "tender_details": email.tender_details,
        "attachments_info": email.attachments_info,
        "processing_status": email.processing_status,
        "is_important": email.is_important,
        "is_notified": email.is_notified,
        "linked_tenders": linked_tenders
    }


@router.get("/{email_id}/tenders")
async def get_email_linked_tenders(
    email_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Получить тендеры, привязанные к письму."""
    email_result = await db.execute(select(Email).where(Email.id == email_id))
    if not email_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Письмо не найдено")
    
    result = await db.execute(
        select(
            Tender.id,
            Tender.purchase_name,
            Tender.notice_number,
            Tender.nmck,
            Tender.status,
            EmailTenderLink.link_type,
            EmailTenderLink.confidence,
            EmailTenderLink.created_at
        )
        .join(EmailTenderLink, Tender.id == EmailTenderLink.tender_id)
        .where(EmailTenderLink.email_id == email_id)
    )
    
    tenders = []
    for row in result.all():
        tenders.append({
            "id": row[0],
            "purchase_name": row[1],
            "notice_number": row[2],
            "nmck": float(row[3]) if row[3] else 0,
            "status": row[4],
            "link_type": row[5],
            "confidence": float(row[6]) if row[6] else 0,
            "linked_at": row[7].isoformat() if row[7] else None
        })
    
    return {"email_id": email_id, "linked_tenders": tenders}


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