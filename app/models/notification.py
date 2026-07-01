from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.database import Base


class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    
    channel_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    config: Mapped[dict] = mapped_column(JSONB, nullable=False)
    
    notify_on_new_email: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_deadline: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_status_change: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_on_manual_link: Mapped[bool] = mapped_column(Boolean, default=True)
    deadline_days_before: Mapped[int] = mapped_column(Integer, default=3)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user: Mapped["User"] = relationship(back_populates="notification_channels")


class Notification(Base):
    __tablename__ = "notifications"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    tender_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tenders.id", ondelete="SET NULL"))
    email_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emails.id", ondelete="SET NULL"))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    channel_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("notification_channels.id", ondelete="SET NULL"))
    
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), default="NORMAL")
    title: Mapped[Optional[str]] = mapped_column(String(500))
    message: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    status: Mapped[str] = mapped_column(String(50), default="PENDING")
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)