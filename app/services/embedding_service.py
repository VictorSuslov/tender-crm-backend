from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.document import Document, DocumentChunk
from app.services.llm_analyzer import LLMAnalyzer
import asyncio


class EmbeddingService:
    @staticmethod
    async def index_document(db: AsyncSession, document_id: int):
        """
        Индексирует документ: разбивает на чанки и создаёт эмбеддинги.
        """
        # Получаем документ
        result = await db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        
        if not document:
            raise ValueError(f"Документ {document_id} не найден")
        
        if not document.content:
            raise ValueError(f"Документ {document_id} не содержит текста")
        
        # Разбиваем на чанки
        chunks = EmbeddingService._split_into_chunks(document.content, chunk_size=500, overlap=50)
        
        # Получаем эмбеддинги
        llm = LLMAnalyzer()
        
        for i, chunk_text in enumerate(chunks):
            # Получаем эмбеддинг
            embedding = await llm.get_embedding(chunk_text)
            
            # Создаём чанк
            chunk = DocumentChunk(
                document_id=document_id,
                tender_id=document.tender_id,
                chunk_index=i,
                content=chunk_text,
                embedding=embedding,
                metadata={"chunk_number": i + 1, "total_chunks": len(chunks)}
            )
            db.add(chunk)
        
        # Обновляем статус документа
        document.is_indexed = True
        document.chunks_count = len(chunks)
        
        await db.commit()
        
        return {"chunks_created": len(chunks)}
    
    @staticmethod
    def _split_into_chunks(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
        """Разбивает текст на чанки с перекрытием."""
        if not text:
            return []
        
        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end]
            chunks.append(chunk)
            start += chunk_size - overlap
        
        return chunks