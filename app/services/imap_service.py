import asyncio
from datetime import datetime
from typing import List, Optional
from imap_tools import MailBox, AND, MailMessage
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import settings
from app.models.email import Email
from app.database import async_session


class IMAPService:
    """Сервис для работы с IMAP-сервером."""
    
    def __init__(self):
        self.server = settings.IMAP_SERVER
        self.login = settings.IMAP_LOGIN
        self.password = settings.IMAP_PASSWORD
    
    def fetch_emails(self, limit: int = 50, folder: str = "INBOX") -> List[dict]:
        """
        Получить последние письма из почтового ящика.
        """
        emails_data = []
        
        try:
            with MailBox(self.server).login(self.login, self.password) as mailbox:
                mailbox.folder.set(folder)
                messages = list(mailbox.fetch(AND(all=True), limit=limit, reverse=True))
                
                for msg in messages:
                    email_data = self._parse_message(msg)
                    emails_data.append(email_data)
                
                print(f"✓ Получено {len(emails_data)} писем из {folder}")
                
        except Exception as e:
            print(f"✗ Ошибка подключения к IMAP: {e}")
        
        return emails_data
    
    def _parse_message(self, msg: MailMessage) -> dict:
        """Парсит письмо в словарь."""
        # Извлекаем текст
        body_text = ""
        if msg.text and len(msg.text.strip()) > 50:
            body_text = msg.text
        elif msg.html:
            import html2text
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0
            body_text = h.handle(msg.html)
        
        # Информация о вложениях (метаданные)
        attachments_info = []
        # Сохраняем содержимое вложений для последующего парсинга
        attachments_payloads = []
        
        for att in msg.attachments:
            attachments_info.append({
                "filename": att.filename,
                "content_type": att.content_type,
                "size_bytes": len(att.payload)
            })
            attachments_payloads.append({
                "info": {
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "size_bytes": len(att.payload)
                },
                "payload": att.payload  # Сохраняем байты
            })
        
        return {
            "uid": msg.uid,
            "folder": "INBOX",
            "from_email": msg.from_,
            "from_name": msg.from_values.name if msg.from_values else None,
            "to_emails": ", ".join(msg.to),
            "subject": msg.subject,
            "body_text": body_text,
            "email_date": msg.date,
            "attachments_info": attachments_info,
            "attachments_payloads": attachments_payloads,
            "has_unsubscribe": "List-Unsubscribe" in msg.headers
        }
    
    async def save_emails_to_db(self, emails_data: List[dict]) -> int:
        """Сохранить письма в базу данных."""
        new_count = 0
        
        async with async_session() as session:
            for email_data in emails_data:
                # Проверяем, есть ли уже такое письмо в БД
                result = await session.execute(
                    select(Email).where(Email.uid == email_data["uid"])
                )
                existing = result.scalar_one_or_none()
                
                if not existing:
                    email = Email(
                        uid=email_data["uid"],
                        folder=email_data["folder"],
                        from_email=email_data["from_email"],
                        from_name=email_data["from_name"],
                        to_emails=email_data["to_emails"],
                        subject=email_data["subject"],
                        body_text=email_data["body_text"],
                        email_date=email_data["email_date"],
                        attachments_info=email_data["attachments_info"],
                        category="GENERAL",
                        processing_status="NEW"
                    )
                    session.add(email)
                    new_count += 1
            
            await session.commit()
        
        print(f"✓ Сохранено {new_count} новых писем в БД")
        return new_count


async def test_imap_connection():
    """Тест подключения к IMAP."""
    service = IMAPService()
    
    print("Тест подключения к IMAP...")
    emails = service.fetch_emails(limit=5)
    
    if emails:
        print(f"\nПолучено {len(emails)} писем:")
        for i, email in enumerate(emails, 1):
            print(f"\n{i}. Тема: {email['subject']}")
            print(f"   От: {email['from_email']}")
            print(f"   Дата: {email['email_date']}")
            print(f"   Вложений: {len(email['attachments_info'])}")
    else:
        print("✗ Не удалось получить письма")
    
    return emails


if __name__ == "__main__":
    asyncio.run(test_imap_connection())