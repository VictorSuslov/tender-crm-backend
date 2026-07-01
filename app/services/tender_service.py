from datetime import datetime
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Optional, List

from app.models.tender import Tender
from app.models.tender_history import TenderHistory
from app.models.email_tender_link import EmailTenderLink
from app.schemas.tender import TenderCreate, TenderUpdate


class TenderService:
    """Сервис для работы с тендерами."""
    
    @staticmethod
    async def get_tenders(
        db: AsyncSession,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        search: Optional[str] = None,
    ) -> tuple[List[Tender], int]:
        """Получить список тендеров с фильтрацией и пагинацией."""
        query = select(Tender)
        
        # Фильтр по статусу
        if status:
            query = query.where(Tender.status == status)
        
        # Поиск по названию или номеру извещения
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                (Tender.purchase_name.ilike(search_pattern)) |
                (Tender.notice_number.ilike(search_pattern)) |
                (Tender.customer_name.ilike(search_pattern))
            )
        
        # Подсчет общего количества
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Пагинация и сортировка (новые первые)
        query = query.order_by(Tender.updated_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        tenders = result.scalars().all()
        
        return tenders, total
    
    @staticmethod
    async def get_tender_by_id(db: AsyncSession, tender_id: int) -> Optional[Tender]:
        """Получить тендер по ID."""
        result = await db.execute(
            select(Tender).where(Tender.id == tender_id)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def create_tender(
        db: AsyncSession,
        tender_data: TenderCreate,
        created_by: Optional[int] = None,
    ) -> Tender:
        """Создать новый тендер."""
        tender = Tender(
            **tender_data.model_dump(),
            created_by=created_by,
            status="NEW",
        )
        db.add(tender)
        await db.flush()  # Получаем ID
        
        # Записываем в историю
        history = TenderHistory(
            tender_id=tender.id,
            user_id=created_by,
            action="CREATED",
            new_value=tender.purchase_name,
        )
        db.add(history)
        
        return tender
    
    @staticmethod
    async def update_tender(
        db: AsyncSession,
        tender_id: int,
        tender_data: TenderUpdate,
        user_id: Optional[int] = None,
    ) -> Optional[Tender]:
        """Обновить тендер."""
        tender = await TenderService.get_tender_by_id(db, tender_id)
        if not tender:
            return None
        
        # Применяем изменения
        update_data = tender_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            old_value = getattr(tender, field)
            if old_value != value:
                setattr(tender, field, value)
                
                # Записываем в историю
                history = TenderHistory(
                    tender_id=tender.id,
                    user_id=user_id,
                    action="UPDATED",
                    field_name=field,
                    old_value=str(old_value) if old_value else None,
                    new_value=str(value) if value else None,
                )
                db.add(history)
        
        return tender
    
    @staticmethod
    async def update_status(
        db: AsyncSession,
        tender_id: int,
        new_status: str,
        result: Optional[str] = None,
        user_id: Optional[int] = None,
        comment: Optional[str] = None,
    ) -> Optional[Tender]:
        """Изменить статус тендера."""
        tender = await TenderService.get_tender_by_id(db, tender_id)
        if not tender:
            return None
        
        old_status = tender.status
        tender.status = new_status
        if result:
            tender.result = result
        
        # Записываем в историю
        history = TenderHistory(
            tender_id=tender.id,
            user_id=user_id,
            action="STATUS_CHANGED",
            field_name="status",
            old_value=old_status,
            new_value=new_status,
            comment=comment,
        )
        db.add(history)
        
        return tender
    
    @staticmethod
    async def delete_tender(
        db: AsyncSession,
        tender_id: int,
        user_id: Optional[int] = None,
    ) -> bool:
        """Мягкое удаление (архивирование) тендера."""
        tender = await TenderService.get_tender_by_id(db, tender_id)
        if not tender:
            return False
        
        old_status = tender.status
        tender.status = "ARCHIVED"
        
        # Записываем в историю
        history = TenderHistory(
            tender_id=tender.id,
            user_id=user_id,
            action="ARCHIVED",
            field_name="status",
            old_value=old_status,
            new_value="ARCHIVED",
        )
        db.add(history)
        
        return True
    
    @staticmethod
    async def get_linked_emails_count(db: AsyncSession, tender_id: int) -> int:
        """Получить количество связанных писем."""
        result = await db.execute(
            select(func.count()).select_from(EmailTenderLink).where(
                EmailTenderLink.tender_id == tender_id
            )
        )
        return result.scalar() or 0