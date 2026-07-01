from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from app.database import Base


class Email(Base):
    __tablename__ = "emails"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Метаданные
    uid: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    message_id: Mapped[Optional[str]] = mapped_column(String(500))
    folder: Mapped[str] = mapped_column(String(100), default="INBOX")
    
    # Отправитель/получатель
    from_email: Mapped[Optional[str]] = mapped_column(String(500))
    from_name: Mapped[Optional[str]] = mapped_column(String(500))
    to_emails: Mapped[Optional[str]] = mapped_column(Text)
    
    # Содержание
    subject: Mapped[Optional[str]] = mapped_column(Text)
    body_text: Mapped[Optional[str]] = mapped_column(Text)
    
    # Классификация
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    llm_model_used: Mapped[Optional[str]] = mapped_column(String(100))
    
    # Извлеченные данные
    tender_details: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Вложения
    attachments_info: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    # Статус
    processing_status: Mapped[str] = mapped_column(String(50), default="NEW")
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    is_notified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Временные метки
    email_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    received_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    
    # Связь с тредом
    thread_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("email_threads.id", ondelete="SET NULL")
    )
    
    # Отношения
    attachments: Mapped[List["EmailAttachment"]] = relationship(back_populates="email")
    tender_links: Mapped[List["EmailTenderLink"]] = relationship(back_populates="email")
    thread: Mapped[Optional["EmailThread"]] = relationship(back_populates="emails")
    
    def __repr__(self) -> str:
        return f"<Email(id={self.id}, category={self.category}, subject={self.subject[:50] if self.subject else None})>"


class EmailAttachment(Base):
    __tablename__ = "email_attachments"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(Integer, ForeignKey("emails.id", ondelete="CASCADE"))
    
    filename: Mapped[Optional[str]] = mapped_column(String(500))
    content_type: Mapped[Optional[str]] = mapped_column(String(200))
    size_bytes: Mapped[Optional[int]] = mapped_column(Integer)
    file_path: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    email: Mapped["Email"] = relationship(back_populates="attachments")


class EmailThread(Base):
    __tablename__ = "email_threads"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    
    subject_template: Mapped[Optional[str]] = mapped_column(Text)
    participants: Mapped[Optional[str]] = mapped_column(Text)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    tender: Mapped["Tender"] = relationship(back_populates="threads")
    emails: Mapped[List["Email"]] = relationship(back_populates="thread")