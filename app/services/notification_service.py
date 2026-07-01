import httpx
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.notification import Notification, NotificationChannel
from app.models.email import Email
from app.models.tender import Tender


class TelegramNotifier:
    """Сервис отправки уведомлений в Telegram с поддержкой прокси."""
    
    def __init__(self):
        self.bot_token = settings.TELEGRAM_BOT_TOKEN
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.proxy_url = getattr(settings, 'TELEGRAM_PROXY_URL', None)
        self.proxy_enabled = getattr(settings, 'TELEGRAM_PROXY_ENABLED', False)
        
        # Создаем httpx клиент с прокси (если настроено)
        self.client = self._create_http_client()
    
    def _create_http_client(self) -> httpx.AsyncClient:
        """Создает HTTP клиент с настройками прокси."""
        if self.proxy_enabled and self.proxy_url:
            print(f"🔐 Telegram: используется прокси {self.proxy_url}")
            return httpx.AsyncClient(
                proxy=self.proxy_url,
                timeout=15
            )
        else:
            return httpx.AsyncClient(timeout=15)
    
    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML"
    ) -> bool:
        """Отправляет сообщение в Telegram."""
        if not self.bot_token:
            print("⚠ TELEGRAM_BOT_TOKEN не настроен")
            return False
        
        try:
            response = await self.client.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                }
            )
            response.raise_for_status()
            return True
        except httpx.ProxyError as e:
            print(f"✗ Ошибка прокси Telegram: {e}")
            return False
        except httpx.ConnectTimeout:
            print("✗ Таймаут подключения к Telegram (возможно, нужен прокси)")
            return False
        except httpx.RequestError as e:
            print(f"✗ Ошибка запроса к Telegram: {e}")
            return False
        except Exception as e:
            print(f"✗ Непредвиденная ошибка отправки в Telegram: {e}")
            return False
    
    async def close(self):
        """Закрывает HTTP клиент."""
        await self.client.aclose()
    
    async def notify_new_tender_email(self, chat_id: str, email) -> bool:
        """Уведомление о новом тендерном письме."""
        text = f"🏆 <b>Новое тендерное письмо!</b>\n\n"
        text += f"📧 <b>От:</b> {email.from_name or email.from_email}\n"
        text += f"📋 <b>Тема:</b> {email.subject or '(без темы)'}\n"
        
        if email.summary:
            text += f"\n📝 <b>Резюме:</b> {email.summary}\n"
        
        if email.tender_details:
            td = email.tender_details
            if td.get("purchase_name"):
                text += f"\n🏗 <b>Закупка:</b> {td['purchase_name']}\n"
            if td.get("nmck"):
                text += f"💰 <b>НМЦК:</b> {td['nmck']}\n"
            if td.get("deadline"):
                text += f"⏰ <b>Срок подачи:</b> {td['deadline']}\n"
            if td.get("notice_number"):
                text += f"🔢 <b>№ извещения:</b> {td['notice_number']}\n"
        
        text += f"\n📅 Дата: {email.email_date.strftime('%d.%m.%Y %H:%M') if email.email_date else 'н/д'}"
        
        return await self.send_message(chat_id, text)
    
    async def notify_linked_tender(self, chat_id: str, email, tender) -> bool:
        """Уведомление о связывании письма с тендером."""
        text = f"🔗 <b>Письмо связано с тендером!</b>\n\n"
        text += f"📋 <b>Тендер:</b> {tender.purchase_name}\n"
        text += f"📊 <b>Статус:</b> {tender.status}\n"
        
        if email.subject:
            text += f"\n📧 <b>Письмо:</b> {email.subject}\n"
        if email.summary:
            text += f"📝 <b>Резюме:</b> {email.summary}\n"
        
        return await self.send_message(chat_id, text)
    
    async def notify_deadline_approaching(self, chat_id: str, tender, days_left: int) -> bool:
        """Уведомление о приближающемся дедлайне."""
        emoji = "⚠️" if days_left <= 1 else "⏰"
        text = f"{emoji} <b>Приближается дедлайн!</b>\n\n"
        text += f"📋 <b>Тендер:</b> {tender.purchase_name}\n"
        text += f"📅 <b>Осталось дней:</b> {days_left}\n"
        
        if tender.nmck:
            text += f"💰 <b>НМЦК:</b> {tender.nmck} {tender.currency}\n"
        if tender.application_deadline:
            text += f"⏰ <b>Дедлайн:</b> {tender.application_deadline.strftime('%d.%m.%Y %H:%M')}\n"
        
        return await self.send_message(chat_id, text)


class NotificationService:
    """Главный сервис управления уведомлениями."""
    
    def __init__(self):
        self.telegram = TelegramNotifier()
    
    async def get_subscribed_users(self, db: AsyncSession) -> List[dict]:
        """Получает список пользователей с настроенными уведомлениями."""
        result = await db.execute(
            select(NotificationChannel).where(
                NotificationChannel.channel_type == "TELEGRAM",
                NotificationChannel.is_enabled == True
            )
        )
        channels = result.scalars().all()
        
        users = []
        for channel in channels:
            users.append({
                "user_id": channel.user_id,
                "chat_id": channel.config.get("chat_id"),
                "notify_on_new_email": channel.notify_on_new_email,
                "notify_on_deadline": channel.notify_on_deadline,
            })
        
        return users
    
    async def notify_new_tender_email(self, db: AsyncSession, email: Email):
        """Уведомляет всех подписчиков о новом тендерном письме."""
        users = await self.get_subscribed_users(db)
        
        for user in users:
            if user.get("notify_on_new_email") and user.get("chat_id"):
                await self.telegram.notify_new_tender_email(
                    user["chat_id"], email
                )
    
    async def test_connection(self, chat_id: str) -> bool:
        """Тестовое сообщение для проверки подключения."""
        text = "✅ <b>Tender CRM подключен!</b>\n\n"
        text += "Теперь вы будете получать уведомления о:\n"
        text += "• 🏆 Новых тендерных письмах\n"
        text += "• 🔗 Связывании писем с тендерами\n"
        text += "• ⏰ Приближающихся дедлайнах\n"
        
        return await self.telegram.send_message(chat_id, text)


# Тестовая функция
async def test_telegram():
    """Тест отправки сообщения в Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        print("✗ TELEGRAM_BOT_TOKEN не настроен в .env")
        return
    
    if not settings.TELEGRAM_CHAT_ID:
        print("✗ TELEGRAM_CHAT_ID не настроен в .env")
        return
    
    notifier = TelegramNotifier()
    
    print("Отправка тестового сообщения...")
    success = await notifier.send_message(
        settings.TELEGRAM_CHAT_ID,
        "✅ Тестовое сообщение от Tender CRM!\n\nЕсли вы видите это сообщение — настройка успешна."
    )
    
    if success:
        print("✓ Сообщение отправлено!")
    else:
        print("✗ Ошибка отправки")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_telegram())