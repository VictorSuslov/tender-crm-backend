import asyncio
from app.services.email_processor import EmailProcessor

async def test_attachment_parsing():
    """Тест парсинга вложений."""
    processor = EmailProcessor()
    
    print("=" * 60)
    print("ТЕСТ ПАРСИНГА ВЛОЖЕНИЙ")
    print("=" * 60)
    
    # Обрабатываем последние 20 писем
    stats = await processor.process_new_emails(limit=20)
    
    print("\n" + "=" * 60)
    print(f"Результаты:")
    print(f"  Получено: {stats['fetched']}")
    print(f"  Новых: {stats['new']}")
    print(f"  Проанализировано: {stats['analyzed']}")
    print(f"  Связано с тендерами: {stats['linked']}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_attachment_parsing())