from typing import List, Optional, Tuple
from sqlalchemy import select, func, delete, cast
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.email import Email
from app.models.email_tender_link import EmailTenderLink
from app.models.tender import Tender


class EmailService:
    """Сервис для работы с письмами."""
    
    @staticmethod
    async def get_emails(
        db: AsyncSession,
        category: Optional[str] = None,
        search: Optional[str] = None,
        is_important: Optional[bool] = None,
        has_attachments: Optional[bool] = None,
        processing_status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Email], int]:
        """Получить список писем с фильтрацией и пагинацией."""
        query = select(Email)
        
        # Фильтр по категории
        if category:
            query = query.where(Email.category == category)
        
        # Поиск по теме, отправителю или резюме
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Email.subject.ilike(search_pattern)) |
                (Email.from_email.ilike(search_pattern)) |
                (Email.summary.ilike(search_pattern)) |
                (Email.body_text.ilike(search_pattern))
            )
        
        # Фильтр по важности
        if is_important is not None:
            query = query.where(Email.is_important == is_important)
        
        # Фильтр по наличию вложений (используем jsonb_array_length)
        if has_attachments is not None:
            if has_attachments:
                query = query.where(func.jsonb_array_length(Email.attachments_info) > 0)
            else:
                query = query.where(func.jsonb_array_length(Email.attachments_info) == 0)
        
        # Фильтр по статусу обработки
        if processing_status:
            query = query.where(Email.processing_status == processing_status)
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Пагинация и сортировка (новые первые)
        query = query.order_by(Email.email_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        emails = result.scalars().all()
        
        return emails, total
    
    @staticmethod
    async def get_email_by_id(db: AsyncSession, email_id: int) -> Optional[Email]:
        """Получить письмо по ID."""
        result = await db.execute(
            select(Email).where(Email.id == email_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_linked_tenders(db: AsyncSession, email_id: int) -> List[int]:
        """Получить список ID тендеров, связанных с письмом."""
        result = await db.execute(
            select(EmailTenderLink.tender_id).where(
                EmailTenderLink.email_id == email_id
            )
        )
        return [row[0] for row in result.all()]
    
    @staticmethod
    async def link_email_to_tender(
        db: AsyncSession,
        email_id: int,
        tender_id: int,
        link_type: str = "MANUAL",
        user_id: Optional[int] = None,
    ) -> bool:
        """Связать письмо с тендером."""
        # Проверяем существование письма и тендера
        email = await EmailService.get_email_by_id(db, email_id)
        if not email:
            return False
        
        tender = await db.execute(
            select(Tender).where(Tender.id == tender_id)
        )
        if not tender.scalar_one_or_none():
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
        
        # Создаем связь
        link = EmailTenderLink(
            email_id=email_id,
            tender_id=tender_id,
            link_type=link_type,
            confidence=1.0 if link_type == "MANUAL" else 0.7
        )
        db.add(link)
        await db.flush()
        
        return True
    
    @staticmethod
    async def unlink_email_from_tender(
        db: AsyncSession,
        email_id: int,
        tender_id: int,
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
    async def get_unlinked_tender_emails(
        db: AsyncSession,
        page: int = 1,
        per_page: int = 20,
    ) -> Tuple[List[Email], int]:
        """Получить тендерные письма без связи с тендерами."""
        # Подзапрос для писем со связями
        linked_emails_subq = select(EmailTenderLink.email_id).subquery()
        
        query = select(Email).where(
            Email.category == "TENDER",
            Email.processing_status == "PROCESSED",
            ~Email.id.in_(select(linked_emails_subq))
        )
        
        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Пагинация
        query = query.order_by(Email.email_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        emails = result.scalars().all()
        
        return emails, total
    
    @staticmethod
    async def get_tender_emails(
        db: AsyncSession,
        tender_id: int,
        page: int = 1,
        per_page: int = 50,
    ) -> Tuple[List[Email], int]:
        """Получить все письма, связанные с конкретным тендером."""
        # Подзапрос для связанных писем
        linked_subq = (
            select(EmailTenderLink.email_id)
            .where(EmailTenderLink.tender_id == tender_id)
            .subquery()
        )
        
        query = select(Email).where(Email.id.in_(select(linked_subq)))
        
        # Подсчет
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Пагинация
        query = query.order_by(Email.email_date.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        emails = result.scalars().all()
        
        return emails, total
    
    @staticmethod
    async def mark_as_important(
        db: AsyncSession,
        email_id: int,
        is_important: bool,
    ) -> Optional[Email]:
        """Отметить письмо как важное/неважное."""
        email = await EmailService.get_email_by_id(db, email_id)
        if not email:
            return None
        
        email.is_important = is_important
        await db.flush()
        
        return email
    
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
        
        # По статусам обработки
        status_result = await db.execute(
            select(Email.processing_status, func.count(Email.id))
            .group_by(Email.processing_status)
        )
        by_status = {row[0]: row[1] for row in status_result.all()}
        
        # С вложениями (используем jsonb_array_length)
        with_attachments_result = await db.execute(
            select(func.count(Email.id)).where(
                func.jsonb_array_length(Email.attachments_info) > 0
            )
        )
        with_attachments = with_attachments_result.scalar()
        
        # Важные
        important_result = await db.execute(
            select(func.count(Email.id)).where(Email.is_important == True)
        )
        important = important_result.scalar()
        
        # Тендерные без связи
        unlinked_result = await db.execute(
            select(func.count(Email.id)).where(
                Email.category == "TENDER",
                Email.processing_status == "PROCESSED",
                ~Email.id.in_(select(EmailTenderLink.email_id))
            )
        )
        unlinked_tenders = unlinked_result.scalar()
        
        return {
            "total": total,
            "by_category": by_category,
            "by_processing_status": by_status,
            "with_attachments": with_attachments,
            "important": important,
            "unlinked_tender_emails": unlinked_tenders,
        }