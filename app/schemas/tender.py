from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class TenderBase(BaseModel):
    """Базовая схема с общими полями."""
    notice_number: Optional[str] = Field(None, description="Номер извещения")
    lot_number: Optional[str] = Field(None, description="Номер лота")
    purchase_name: str = Field(..., min_length=3, description="Название закупки")
    customer_name: Optional[str] = Field(None, description="Заказчик")
    etp_url: Optional[str] = Field(None, description="Ссылка на ЭТП")
    nmck: Optional[Decimal] = Field(None, description="НМЦК")
    currency: str = Field("RUB", description="Валюта")
    publication_date: Optional[date] = Field(None, description="Дата публикации")
    application_deadline: Optional[datetime] = Field(None, description="Срок подачи заявок")
    auction_date: Optional[datetime] = Field(None, description="Дата аукциона")
    contract_deadline: Optional[date] = Field(None, description="Срок исполнения контракта")
    notes: Optional[str] = Field(None, description="Заметки")


class TenderCreate(TenderBase):
    """Схема для создания тендера."""
    responsible_user_id: Optional[int] = Field(None, description="ID ответственного")


class TenderUpdate(BaseModel):
    """Схема для обновления тендера (все поля опциональны)."""
    notice_number: Optional[str] = None
    lot_number: Optional[str] = None
    purchase_name: Optional[str] = None
    customer_name: Optional[str] = None
    etp_url: Optional[str] = None
    nmck: Optional[Decimal] = None
    currency: Optional[str] = None
    publication_date: Optional[date] = None
    application_deadline: Optional[datetime] = None
    auction_date: Optional[datetime] = None
    contract_deadline: Optional[date] = None
    responsible_user_id: Optional[int] = None
    notes: Optional[str] = None


class TenderStatusUpdate(BaseModel):
    """Схема для изменения статуса тендера."""
    status: str = Field(..., description="Новый статус")
    result: Optional[str] = Field(None, description="Результат (для WON/LOST)")
    comment: Optional[str] = Field(None, description="Комментарий к изменению")


class TenderRead(BaseModel):
    """Схема для чтения тендера (включает вычисляемые поля)."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    status: str
    result: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    # Наследуем поля из TenderBase
    notice_number: Optional[str]
    lot_number: Optional[str]
    purchase_name: str
    customer_name: Optional[str]
    etp_url: Optional[str]
    nmck: Optional[Decimal]
    currency: str
    publication_date: Optional[date]
    application_deadline: Optional[datetime]
    auction_date: Optional[datetime]
    contract_deadline: Optional[date]
    notes: Optional[str]
    
    # Вычисляемые поля
    responsible_user_id: Optional[int]
    created_by: Optional[int]
    
    # Дополнительные поля (заполняются отдельно)
    linked_emails_count: int = 0
    last_email_date: Optional[datetime] = None


class TenderList(BaseModel):
    """Схема для списка тендеров с пагинацией."""
    items: list[TenderRead]
    total: int
    page: int
    per_page: int