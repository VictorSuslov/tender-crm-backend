from datetime import datetime
from sqlalchemy import String, Text, DateTime, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from typing import Optional, List

from app.database import Base


class Document(Base):
    """Документ тендера (заявка, доп. соглашение, заметка, письмо)."""
    __tablename__ = "documents"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    tender_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    email_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("emails.id", ondelete="SET NULL"))
    
    doc_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    source_path: Mapped[Optional[str]] = mapped_column(Text)
    
    doc_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False)
    indexed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tender = relationship("Tender", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    """Чанк документа с эмбеддингом."""
    __tablename__ = "document_chunks"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    tender_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenders.id", ondelete="CASCADE"))
    
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Используем pgvector.sqlalchemy.Vector для правильной работы с типом vector
    embedding = mapped_column(Vector(1024))
    
    chunk_metadata: Mapped[Optional[dict]] = mapped_column("metadata", JSONB)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # Relationships
    document = relationship("Document", back_populates="chunks")