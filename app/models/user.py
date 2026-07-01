from datetime import datetime
from sqlalchemy import String, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from app.database import Base


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    telegram_chat_id: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Настройки уведомлений
    notify_telegram: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_email: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_desktop: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Роль
    role: Mapped[str] = mapped_column(String(50), default="USER")
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Отношения
    notification_channels: Mapped[List["NotificationChannel"]] = relationship(back_populates="user")
    tenders_responsible: Mapped[List["Tender"]] = relationship(
        back_populates="responsible_user",
        foreign_keys="Tender.responsible_user_id"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username})>"