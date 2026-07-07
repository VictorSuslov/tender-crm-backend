from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, ConfigDict


class EmailAttachmentRead(BaseModel):
    """Схема вложения письма."""
    filename: str
    content_type: Optional[str] = None
    size_bytes: Optional[int] = None


class TenderDetailsRead(BaseModel):
    """Схема извлеченных данных тендера."""
    notice_number: Optional[str] = None
    purchase_name: Optional[str] = None
    nmck: Optional[str] = None
    deadline: Optional[str] = None
    
class EmailTenderLinkRead(BaseModel):
    tender_id: int
    link_type: str
    tender_name: Optional[str] = None
    
    class Config:
        from_attributes = True


class EmailRead(BaseModel):
    """Схема чтения письма."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    uid: str
    folder: str
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    to_emails: Optional[str] = None
    subject: Optional[str] = None
    body_text: Optional[str] = None
    body_html: Optional[str] = None
    
    category: str
    summary: Optional[str] = None
    llm_model_used: Optional[str] = None
    tender_details: Optional[dict] = None
    
    attachments_info: Optional[list] = None
    processing_status: str
    is_important: bool
    is_notified: bool
    
    email_date: Optional[datetime] = None
    received_at: datetime
    processed_at: Optional[datetime] = None
    
    # Дополнительные поля (заполняются отдельно)
    linked_tenders: List[EmailTenderLinkRead] = []


class EmailList(BaseModel):
    """Схема списка писем с пагинацией."""
    model_config = ConfigDict(from_attributes=True)
    
    items: List[EmailRead]
    total: int
    page: int = 1
    per_page: int = 50


class EmailLinkCreate(BaseModel):
    """Схема для связывания письма с тендером."""
    tender_id: int = Field(..., description="ID тендера")
    link_type: str = Field(default="MANUAL", description="Тип связи")