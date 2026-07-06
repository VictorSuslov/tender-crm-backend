from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Tuple, List
from app.models.email import Email
from app.models.tender import Tender
from app.models.email_tender_link import EmailTenderLink


class EmailService:
    """Сервис для работы с письмами."""
    
    @staticmethod
    async def get_email_by_id(db: AsyncSession, email_id: int) -> Optional[Email]:
        """Получить письмо по ID."""
        result = await db.execute(select(Email).where(Email.id == email_id))
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_statistics(db: AsyncSession) -> dict:
        """Получить статистику по письмам."""
        # Общее количество
        total_result = await db.execute(select(func.count(Email.id)))
        total = total_result.scalar()
        
        # По категориям
        category_result = await db.execute(
            select(Email.category, func.count(Email.id))
            .group_by(Email.category)
        )
        by_category = {row[0]: row[1] for row in category_result.all()}
        
        # Тендерные письма
        tender_count = by_category.get("TENDER", 0)
        
        # Связанные с тендерами
        linked_result = await db.execute(
            select(func.count(EmailTenderLink.email_id.distinct()))
        )
        linked = linked_result.scalar()
        
        return {
            "total": total,
            "by_category": by_category,
            "tender_emails": tender_count,
            "linked_to_tenders": linked,
            "unlinked_tender_emails": tender_count - linked,
        }
    
    @staticmethod
    async def get_unlinked_tender_emails(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[Email], int]:
        """Получить тендерные письма без связи с тендерами."""
        # Подзапрос для связанных писем
        linked_emails_subq = (
            select(EmailTenderLink.email_id)
            .distinct()
            .subquery()
        )
        
        # Основной запрос
        query = (
            select(Email)
            .where(Email.category == "TENDER")
            .where(~Email.id.in_(select(linked_emails_subq.c.email_id)))
            .order_by(Email.email_date.desc())
        )
        
        # Общее количество
        count_query = (
            select(func.count(Email.id))
            .where(Email.category == "TENDER")
            .where(~Email.id.in_(select(linked_emails_subq.c.email_id)))
        )
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Пагинация
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        emails = result.scalars().all()
        
        return emails, total
    
    @staticmethod
    async def get_linked_tenders(db: AsyncSession, email_id: int) -> List[dict]:
        """Получить тендеры, связанные с письмом."""
        result = await db.execute(
            select(Tender)
            .join(EmailTenderLink, Tender.id == EmailTenderLink.tender_id)
            .where(EmailTenderLink.email_id == email_id)
        )
        tenders = result.scalars().all()
        
        return [
            {
                "id": t.id,
                "purchase_name": t.purchase_name,
                "notice_number": t.notice_number,
                "status": t.status,
            }
            for t in tenders
        ]
    
    @staticmethod
    async def link_email_to_tender(
        db: AsyncSession,
        email_id: int,
        tender_id: int,
        link_type: str = "MANUAL"
    ) -> bool:
        """Связать письмо с тендером."""
        # Проверяем существование
        email = await EmailService.get_email_by_id(db, email_id)
        if not email:
            return False
        
        tender_result = await db.execute(select(Tender).where(Tender.id == tender_id))
        if not tender_result.scalar_one_or_none():
            return False
        
        # Проверяем, нет ли уже такой связи
        existing = await db.execute(
            select(EmailTenderLink).where(
                EmailTenderLink.email_id == email_id,
                EmailTenderLink.tender_id == tender_id
            )
        )
        if existing.scalar_one_or_none():
            return True  # Уже связано
        
        # Создаём связь
        link = EmailTenderLink(
            email_id=email_id,
            tender_id=tender_id,
            link_type=link_type,
            confidence=1.0 if link_type == "MANUAL" else 0.5
        )
        db.add(link)
        return True
    
    @staticmethod
    async def unlink_email_from_tender(
        db: AsyncSession,
        email_id: int,
        tender_id: int
    ) -> bool:
        """Удалить связь письма с тендером."""
        result = await db.execute(
            delete(EmailTenderLink).where(
                EmailTenderLink.email_id == email_id,
                EmailTenderLink.tender_id == tender_id
            )
        )
        return result.rowcount > 0
    
    @staticmethod
    async def mark_as_important(
        db: AsyncSession,
        email_id: int,
        is_important: bool
    ) -> Optional[Email]:
        """Отметить письмо как важное/неважное."""
        email = await EmailService.get_email_by_id(db, email_id)
        if not email:
            return None
        
        email.is_important = is_important
        return email