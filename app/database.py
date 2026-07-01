from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


# Создаем async engine для подключения к PostgreSQL
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Вывод SQL-запросов в консоль при DEBUG=true
    pool_pre_ping=True,   # Проверка соединения перед использованием
    pool_size=10,
    max_overflow=20,
)

# Фабрика сессий
async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Базовый класс для всех SQLAlchemy моделей."""
    pass


async def get_db() -> AsyncSession:
    """Dependency для получения сессии БД в эндпоинтах."""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def test_connection() -> bool:
    """Проверка подключения к БД."""
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                __import__('sqlalchemy').text("SELECT version();")
            )
            version = result.scalar()
            print(f"✓ PostgreSQL подключен: {version}")
            return True
    except Exception as e:
        print(f"✗ Ошибка подключения к БД: {e}")
        return False