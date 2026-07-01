from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Text, Date, DateTime, Integer, Numeric, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional, List

from app.database import Base


class Tender(Base):
    __tablename__ = "tenders"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    
    # Основная информация
    notice_number: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    lot_number: Mapped[Optional[str]] = mapped_column(String(100))
    purchase_name: Mapped[str] = mapped_column(Text, nullable=False)
    customer_name: Mapped[Optional[str]] = mapped_column(String(500))
    etp_url: Mapped[Optional[str]] = mapped_column(Text)
    
    # Финансовые данные
    nmck: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(10), default="RUB")
    
    # Сроки
    publication_date: Mapped[Optional[date]] = mapped_column(Date)
    application_deadline: Mapped[Optional[datetime]] = mapped_column(DateTime)
    auction_date: Mapped[Optional[datetime]] = mapped_column(DateTime)
    contract_deadline: Mapped[Optional[date]] = mapped_column(Date)
    
    # Статус
    status: Mapped[str] = mapped_column(String(50), default="NEW")
    result: Mapped[Optional[str]] = mapped_column(String(50))
    
    # Ответственный
    responsible_user_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Метаданные
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Отношения
    responsible_user: Mapped[Optional["User"]] = relationship(
        back_populates="tenders_responsible",
        foreign_keys=[responsible_user_id]
    )
    email_links: Mapped[List["EmailTenderLink"]] = relationship(back_populates="tender")
    threads: Mapped[List["EmailThread"]] = relationship(back_populates="tender")
    history: Mapped[List["TenderHistory"]] = relationship(back_populates="tender")
    documents: Mapped[List["Document"]] = relationship("Document", back_populates="tender")
    
    def __repr__(self) -> str:
        return f"<Tender(id={self.id}, notice_number={self.notice_number}, status={self.status})>"