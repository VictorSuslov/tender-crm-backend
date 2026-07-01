from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class DocumentCreate(BaseModel):
    """Схема создания документа."""
    doc_type: str = Field(..., description="Тип документа: TENDER_APPLICATION, SUPPLEMENT, EMAIL, NOTE")
    title: str = Field(..., min_length=1, max_length=500, description="Заголовок документа")
    content: str = Field(..., min_length=1, description="Содержимое документа")
    source_path: Optional[str] = Field(None, description="Путь к исходному файлу")
    metadata: Optional[dict] = Field(None, description="Дополнительные метаданные")


class DocumentRead(BaseModel):
    """Схема чтения документа."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    tender_id: int
    email_id: Optional[int] = None
    doc_type: str
    title: str
    content: str
    source_path: Optional[str] = None
    
    # ВАЖНО: используем doc_metadata для соответствия SQLAlchemy модели
    doc_metadata: Optional[dict] = Field(None, alias="doc_metadata")
    
    is_indexed: bool
    indexed_at: Optional[datetime] = None
    chunks_count: int
    
    created_at: datetime
    updated_at: datetime
    
    # Для обратной совместимости можно добавить свойство
    @property
    def metadata(self) -> Optional[dict]:
        return self.doc_metadata


class DocumentList(BaseModel):
    """Схема списка документов."""
    items: List[DocumentRead]
    total: int


class DocumentIndexResult(BaseModel):
    """Результат индексации документа."""
    document_id: int
    chunks_count: int
    indexed_at: datetime
    processing_time_ms: int


class DocumentFromEmail(BaseModel):
    """Создание документа из письма."""
    include_attachments_text: bool = Field(
        default=True,
        description="Включить текст из вложений в содержимое документа"
    )


class SearchChunk(BaseModel):
    """Найденный чанк документа."""
    chunk_id: int
    document_id: int
    tender_id: int
    chunk_index: int
    content: str
    metadata: Optional[dict] = None
    document_title: str
    doc_type: str
    similarity: float


class SearchResult(BaseModel):
    """Результат семантического поиска."""
    query: str
    tender_id: Optional[int] = None
    chunks: List[SearchChunk]
    total_found: int
    processing_time_ms: int


class RagQueryRequest(BaseModel):
    """Запрос к RAG-системе."""
    question: str = Field(..., min_length=3, max_length=1000, description="Вопрос пользователя")
    tender_id: Optional[int] = Field(None, description="ID тендера для фильтрации (null = все тендеры)")
    top_k: int = Field(default=5, ge=1, le=20, description="Количество релевантных чанков")


class RagQueryResponse(BaseModel):
    """Ответ RAG-системы."""
    answer: str
    sources: List[SearchChunk]
    processing_time_ms: int
    tender_id: Optional[int] = None
    question: str


class RagHistoryItem(BaseModel):
    """Элемент истории RAG-запросов."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: Optional[int] = None
    tender_id: Optional[int] = None
    query: str
    answer: Optional[str] = None
    sources_count: int
    processing_time_ms: Optional[int] = None
    created_at: datetime


class RagHistoryList(BaseModel):
    """Список истории запросов."""
    items: List[RagHistoryItem]
    total: int