import asyncio
from app.services.email_processor import EmailProcessor

async def test_email_processor():
    """Тест полного пайплайна обработки 50 писем."""
    processor = EmailProcessor()
    
    print("\nЗапуск теста обработки 50 писем...")
    print("Это займет примерно 2-3 минуты\n")
    
    stats = await processor.process_new_emails(limit=50)
    
    print("\n✓ Тест завершен")
    return stats

if __name__ == "__main__":
    asyncio.run(test_email_processor())