from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, DateTime, Integer, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from app.database import Base


class EmailTenderLink(Base):
    __tablename__ = "email_tender_links"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email_id: Mapped[int] = mapped_column(Integer, ForeignKey("emails.id", ondelete="CASCADE"))
    tender_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    
    link_type: Mapped[str] = mapped_column(String(50), nullable=False)
    confidence: Mapped[Optional[Decimal]] = mapped_column(Numeric(3, 2))
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Отношения (используем строковые ссылки для избежания циклического импорта)
    email: Mapped["Email"] = relationship(back_populates="tender_links")
    tender: Mapped["Tender"] = relationship(back_populates="email_links")