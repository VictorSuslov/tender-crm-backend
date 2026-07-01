from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from typing import Optional

from app.database import Base


class RagQuery(Base):
    """Запись истории RAG-запросов."""
    __tablename__ = "rag_queries"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    tender_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("tenders.id", ondelete="SET NULL"))
    
    query: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    sources_count: Mapped[int] = mapped_column(Integer, default=0)
    sources: Mapped[Optional[dict]] = mapped_column(JSONB)
    
    processing_time_ms: Mapped[Optional[int]] = mapped_column(Integer)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)