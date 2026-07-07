from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.tender import Tender
from app.models.email_tender_link import EmailTenderLink
from datetime import datetime
import re


class TenderLinker:
    """Сервис для автоматической привязки писем к существующим тендерам."""
    
    @staticmethod
    async def try_link_email(
        db: AsyncSession,
        email_id: int,
        tender_details: dict
    ) -> dict:
        """
        Пытается привязать письмо к существующему тендеру.
        Если не получилось — ничего не делает, письмо остаётся в категории TENDER.
        
        Returns:
            {"linked": True/False, "tender_id": int или None, "method": str или None}
        """
        if not tender_details:
            return {"linked": False, "tender_id": None, "method": None}
        
        notice_number = tender_details.get("notice_number")
        purchase_name = tender_details.get("purchase_name")
        
        # Стратегия 1: Поиск по номеру извещения
        if notice_number and notice_number.strip():
            notice_clean = re.sub(r"[^0-9]", "", notice_number)
            
            result = await db.execute(
                select(Tender).where(
                    Tender.notice_number.ilike(f"%{notice_clean}%")
                )
            )
            tender = result.scalar_one_or_none()
            
            if tender:
                await TenderLinker._create_link(db, email_id, tender.id)
                print(f"  🔗 Привязка по номеру: {notice_clean} → Тендер ID={tender.id}")
                return {
                    "linked": True,
                    "tender_id": tender.id,
                    "method": "notice_number"
                }
        
        # Стратегия 2: Поиск по названию закупки
        if purchase_name and len(purchase_name.strip()) > 10:
            result = await db.execute(
                select(Tender).where(
                    Tender.purchase_name.ilike(f"%{purchase_name[:50]}%")
                ).limit(5)
            )
            candidates = result.scalars().all()
            
            for tender in candidates:
                similarity = TenderLinker._calculate_similarity(
                    purchase_name, tender.purchase_name
                )
                if similarity > 0.6:
                    await TenderLinker._create_link(db, email_id, tender.id)
                    print(f"  🔗 Привязка по названию (sim={similarity:.2f}) → Тендер ID={tender.id}")
                    return {
                        "linked": True,
                        "tender_id": tender.id,
                        "method": "purchase_name"
                    }
        
        # Не нашли — ничего не делаем, письмо остаётся в категории TENDER
        return {"linked": False, "tender_id": None, "method": None}
    
    @staticmethod
    def _calculate_similarity(text1: str, text2: str) -> float:
        """Простая оценка похожести двух строк по ключевым словам."""
        words1 = {w for w in text1.lower().split() if len(w) >= 4}
        words2 = {w for w in text2.lower().split() if len(w) >= 4}
        
        if not words1 or not words2:
            return 0.0
        
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union) if union else 0.0
    
    @staticmethod
    async def _create_link(db: AsyncSession, email_id: int, tender_id: int):
        """Создаёт связь, если её ещё нет."""
        result = await db.execute(
            select(EmailTenderLink).where(
                and_(
                    EmailTenderLink.email_id == email_id,
                    EmailTenderLink.tender_id == tender_id
                )
            )
        )
        
        if result.scalar_one_or_none():
            return
        
        link = EmailTenderLink(
            email_id=email_id,
            tender_id=tender_id,
            created_at=datetime.utcnow()
        )
        db.add(link)
        await db.flush()