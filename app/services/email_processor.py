import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import async_session
from app.models.email import Email
from app.models.tender import Tender
from app.models.email_tender_link import EmailTenderLink
from app.services.imap_service import IMAPService
from app.services.llm_analyzer import LLMAnalyzer


class EmailProcessor:
    """
    Полный пайплайн обработки писем:
    1. Получение писем из IMAP
    2. Анализ через LLM
    3. Сохранение в БД
    4. Автоматическое связывание с тендерами
    """
    
    def __init__(self):
        self.imap_service = IMAPService()
        self.llm_analyzer = LLMAnalyzer()
    
    async def process_new_emails(self, limit: int = 50) -> Dict[str, int]:
        """
        Основной метод обработки новых писем.
        """
        stats = {
            "fetched": 0,
            "new": 0,
            "analyzed": 0,
            "linked": 0
        }
        
        print("=" * 60)
        print(f"НАЧАЛО ОБРАБОТКИ ПИСЕМ: {datetime.now()}")
        print("=" * 60)
        
        # Шаг 1: Получение писем из IMAP
        print("\n[1/4] Получение писем из IMAP...")
        emails_data = self.imap_service.fetch_emails(limit=limit)
        stats["fetched"] = len(emails_data)
        
        if not emails_data:
            print("✗ Письма не получены")
            return stats
        
        # Шаг 2: Фильтрация новых писем
        print("\n[2/4] Проверка новых писем...")
        new_emails = await self._filter_new_emails(emails_data)
        stats["new"] = len(new_emails)
        
        if not new_emails:
            print("✓ Новых писем нет")
            return stats
        
        print(f"✓ Найдено {len(new_emails)} новых писем")
        
        # Шаг 3: Анализ через LLM и сохранение в БД
        print("\n[3/4] Анализ писем через LLM...")
        for i, email_data in enumerate(new_emails, 1):
            print(f"\n  Обработка письма {i}/{len(new_emails)}: {email_data['subject'][:50]}...")
            
            # Извлекаем текст из вложений
            attachments_text = ""
            if email_data.get("attachments_payloads"):
                print(f"    📎 Вложений: {len(email_data['attachments_payloads'])}")
                extracted_parts = []
                for att in email_data["attachments_payloads"]:
                    att_text = self.llm_analyzer.extract_text_from_attachment(
                        att["info"], att["payload"]
                    )
                    if att_text:
                        extracted_parts.append(f"[Файл: {att['info']['filename']}]\n{att_text}")
                        print(f"       ✓ {att['info']['filename']}: извлечено {len(att_text)} символов")
                    else:
                        print(f"       ⚠ {att['info']['filename']}: текст не извлечен")
                
                if extracted_parts:
                    attachments_text = "\n\n".join(extracted_parts)
            
            # Анализ через LLM (с текстом из вложений)
            analysis = await self.llm_analyzer.analyze_email(
                subject=email_data["subject"],
                body_text=email_data["body_text"],
                from_email=email_data["from_email"],
                attachments_text=attachments_text
            )
            
            print(f"    Категория: {analysis.get('category')}")
            print(f"    Резюме: {analysis.get('summary')[:80]}...")
            
            # Сохранение в БД
            await self._save_email_to_db(email_data, analysis)
            stats["analyzed"] += 1
        
        # Шаг 4: Автоматическое связывание с тендерами
        print("\n[4/4] Связывание писем с тендерами...")
        linked_count = await self._auto_link_emails_to_tenders()
        stats["linked"] = linked_count
        
        print("\n" + "=" * 60)
        print("РЕЗУЛЬТАТЫ ОБРАБОТКИ:")
        print(f"  Получено писем: {stats['fetched']}")
        print(f"  Новых писем: {stats['new']}")
        print(f"  Проанализировано: {stats['analyzed']}")
        print(f"  Связано с тендерами: {stats['linked']}")
        print("=" * 60)
        
        return stats
    
    async def _filter_new_emails(self, emails_data: List[dict]) -> List[dict]:
        """Фильтрует только новые письма (которых нет в БД)."""
        new_emails = []
        
        async with async_session() as session:
            for email_data in emails_data:
                result = await session.execute(
                    select(Email).where(Email.uid == email_data["uid"])
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    new_emails.append(email_data)
        
        return new_emails
    
    async def _save_email_to_db(self, email_data: dict, analysis: dict):
        """Сохраняет письмо с результатами анализа в БД."""
        async with async_session() as session:
            # 1. Преобразуем email_date из aware datetime в naive datetime
            email_date = email_data.get("email_date")
            if email_date and hasattr(email_date, 'tzinfo') and email_date.tzinfo is not None:
                email_date = email_date.replace(tzinfo=None)
            
            # 2. Обработка tender_details
            tender_details = analysis.get("tender_details")
            if tender_details is None or (isinstance(tender_details, str) and tender_details.lower() in ["null", "none", ""]):
                tender_details = None
            elif isinstance(tender_details, dict) and not any(tender_details.values()):
                tender_details = None
            
            # 3. Создаем объект Email
            email = Email(
                uid=email_data["uid"],
                folder=email_data.get("folder", "INBOX"),
                from_email=email_data.get("from_email"),
                from_name=email_data.get("from_name"),
                to_emails=email_data.get("to_emails"),
                subject=email_data.get("subject"),
                body_text=email_data.get("body_text", ""),
                body_html=email_data.get("body_html", ""),  # ← НОВОЕ ПОЛЕ
                email_date=email_date,
                attachments_info=email_data.get("attachments_info"),
                category=analysis.get("category", "GENERAL"),
                summary=analysis.get("summary"),
                llm_model_used="qwen2.5:7b",
                tender_details=tender_details,
                processing_status="PROCESSED",
                processed_at=datetime.utcnow()
            )
            session.add(email)
            await session.commit()
    
    async def _auto_link_emails_to_tenders(self) -> int:
        """Автоматически связывает новые письма с тендерами."""
        linked_count = 0
        
        async with async_session() as session:
            # Получаем все новые тендерные письма без связей
            result = await session.execute(
                select(Email).where(
                    Email.category == "TENDER",
                    Email.processing_status == "PROCESSED"
                )
            )
            tender_emails = result.scalars().all()
            
            for email in tender_emails:
                # Проверяем, есть ли уже связь
                existing_link = await session.execute(
                    select(EmailTenderLink).where(
                        EmailTenderLink.email_id == email.id
                    )
                )
                if existing_link.scalar_one_or_none():
                    continue
                
                # Пытаемся связать
                tender_id = await self._find_matching_tender(session, email)
                
                if tender_id:
                    # Создаем связь
                    link = EmailTenderLink(
                        email_id=email.id,
                        tender_id=tender_id,
                        link_type="AUTO_NOTICE",
                        confidence=1.0
                    )
                    session.add(link)
                    linked_count += 1
                    print(f"  ✓ Связано письмо '{email.subject[:40]}...' с тендером ID={tender_id}")
            
            await session.commit()
        
        return linked_count
    
    async def _find_matching_tender(self, session: AsyncSession, email: Email) -> Optional[int]:
        """Ищет подходящий тендер для письма."""
        if not email.tender_details:
            return None
        
        import re
        
        # Уровень 1: Поиск по номеру извещения (нечёткий)
        notice_number = email.tender_details.get("notice_number")
        if notice_number and notice_number.strip():
            # Очищаем номер от лишних символов
            notice_clean = re.sub(r"[^0-9]", "", notice_number)
            
            if notice_clean:
                result = await session.execute(
                    select(Tender).where(
                        Tender.notice_number.ilike(f"%{notice_clean}%"),
                        Tender.status.in_(['NEW', 'IN_PROGRESS', 'SUBMITTED', 'WON'])
                    )
                )
                tender = result.scalar_one_or_none()
                if tender:
                    print(f"    🔗 Найдено совпадение по номеру: {notice_clean}")
                    return tender.id
        
        # Уровень 2: Нечеткий поиск по названию закупки
        purchase_name = email.tender_details.get("purchase_name")
        if purchase_name and len(purchase_name.strip()) > 15:
            # Используем pg_trgm similarity
            result = await session.execute(
                select(Tender).where(
                    Tender.status.in_(['NEW', 'IN_PROGRESS', 'SUBMITTED', 'WON']),
                    func.similarity(Tender.purchase_name, purchase_name) > 0.5
                ).order_by(
                    func.similarity(Tender.purchase_name, purchase_name).desc()
                ).limit(1)
            )
            tender = result.scalar_one_or_none()
            if tender:
                similarity = await session.execute(
                    select(func.similarity(Tender.purchase_name, purchase_name))
                    .where(Tender.id == tender.id)
                )
                sim_value = similarity.scalar()
                print(f"    🔗 Найдено совпадение по названию (similarity={sim_value:.2f})")
                return tender.id
        
        return None


async def test_email_processor():
    """Тест полного пайплайна обработки писем."""
    processor = EmailProcessor()
    
    print("\nЗапуск теста обработки писем...")
    print("Будут обработаны последние 10 писем из INBOX\n")
    
    stats = await processor.process_new_emails(limit=10)
    
    print("\n✓ Тест завершен")
    return stats


if __name__ == "__main__":
    asyncio.run(test_email_processor())