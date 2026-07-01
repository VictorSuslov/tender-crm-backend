import asyncio
from app.services.notification_service import TelegramNotifier

async def test_telegram():
    """Тест отправки сообщения в Telegram."""
    from app.config import settings
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("✗ TELEGRAM_BOT_TOKEN не настроен в .env")
        return
    
    if not settings.TELEGRAM_CHAT_ID:
        print("✗ TELEGRAM_CHAT_ID не настроен в .env")
        return
    
    notifier = TelegramNotifier()
    
    print(f"Прокси включен: {notifier.proxy_enabled}")
    print(f"URL прокси: {notifier.proxy_url or 'не используется'}")
    print("\nОтправка тестового сообщения...")
    
    try:
        success = await notifier.send_message(
            settings.TELEGRAM_CHAT_ID,
            "✅ Тестовое сообщение от Tender CRM!\n\n"
            f"Прокси: {'включен' if notifier.proxy_enabled else 'выключен'}"
        )
        
        if success:
            print("✓ Сообщение отправлено!")
        else:
            print("✗ Ошибка отправки. Проверьте прокси.")
    finally:
        await notifier.close()


if __name__ == "__main__":
    asyncio.run(test_telegram())