import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.database import async_session
from app.models.system_settings import SystemSetting
from app.services.email_processor import EmailProcessor


class IMAPWorker:
    """Фоновый воркер для периодической обработки писем."""
    
    def __init__(self):
        self.processor = EmailProcessor()
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self._started = False
    
    async def get_check_interval(self) -> int:
        """Получает интервал проверки из настроек."""
        async with async_session() as session:
            result = await session.execute(
                select(SystemSetting).where(SystemSetting.key == "imap_check_interval_minutes")
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                try:
                    return int(setting.value)
                except ValueError:
                    pass
            
            return 5  # По умолчанию 5 минут
    
    async def process_emails_job(self):
        """Задача обработки писем."""
        if self.is_running:
            print("⚠ Предыдущая задача еще выполняется, пропускаем")
            return
        
        self.is_running = True
        try:
            print(f"\n{'='*60}")
            print(f"ЗАПУСК АВТОМАТИЧЕСКОЙ ОБРАБОТКИ")
            print(f"{'='*60}\n")
            
            stats = await self.processor.process_new_emails(limit=50)
            
            print(f"\n✓ Автоматическая обработка завершена")
            print(f"  Новых писем: {stats['new']}")
            print(f"  Проанализировано: {stats['analyzed']}")
            print(f"  Связано с тендерами: {stats['linked']}")
            
        except Exception as e:
            print(f"✗ Ошибка при обработке писем: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.is_running = False
    
    async def start(self):
        """Запускает планировщик (асинхронный метод)."""
        if self._started:
            print("⚠ IMAP воркер уже запущен")
            return
        
        # Получаем интервал асинхронно
        interval = await self.get_check_interval()
        
        print(f"🔄 Запуск IMAP воркера (интервал: {interval} минут)")
        
        self.scheduler.add_job(
            self.process_emails_job,
            trigger=IntervalTrigger(minutes=interval),
            id="imap_check",
            name="Проверка IMAP",
            replace_existing=True,
            next_run_time=None  # Не запускать сразу при старте
        )
        
        self.scheduler.start()
        self._started = True
        print(f"✓ IMAP воркер запущен")
    
    def stop(self):
        """Останавливает планировщик."""
        if self._started and self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            self._started = False
            print("✓ IMAP воркер остановлен")


# Глобальный экземпляр воркера
imap_worker = IMAPWorker()