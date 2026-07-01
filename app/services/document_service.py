from typing import List, Optional
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from app.database import async_session
from app.models.document import Document, DocumentChunk
from app.services.embedding_service import embedding_service
from app.config import settings


class DocumentService:
    """Сервис для работы с документами и их индексацией."""
    
    @staticmethod
    async def create_document(
        tender_id: int,
        doc_type: str,
        title: str,
        content: str,
        email_id: Optional[int] = None,
        metadata: Optional[dict] = None,
    ) -> Document:
        """Создать новый документ."""
        async with async_session() as session:
            doc = Document(
                tender_id=tender_id,
                email_id=email_id,
                doc_type=doc_type,
                title=title,
                content=content,
                doc_metadata=metadata or {},
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            return doc
    
    @staticmethod
    async def get_document_by_id(document_id: int) -> Optional[Document]:
        """Получить документ по ID."""
        async with async_session() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            return result.scalar_one_or_none()
    
    @staticmethod
    async def get_documents_by_tender(tender_id: int) -> List[Document]:
        """Получить все документы тендера."""
        async with async_session() as session:
            result = await session.execute(
                select(Document).where(Document.tender_id == tender_id)
            )
            return result.scalars().all()
    
    @staticmethod
    def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
        """
        Разбить текст на чанки с перекрытием.
        
        Стратегия: разбиваем по абзацам, затем объединяем до chunk_size.
        """
        chunk_size = chunk_size or settings.RAG_CHUNK_SIZE
        overlap = overlap or settings.RAG_CHUNK_OVERLAP
        
        if not text or not text.strip():
            return []
        
        # Разбиваем по абзацам
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            # Если абзац слишком длинный, разбиваем по предложениям
            if len(para) > chunk_size:
                sentences = para.replace('. ', '.\n').split('\n')
                for sent in sentences:
                    sent = sent.strip()
                    if not sent:
                        continue
                    
                    if len(current_chunk) + len(sent) < chunk_size:
                        current_chunk += sent + " "
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sent + " "
            else:
                if len(current_chunk) + len(para) < chunk_size:
                    current_chunk += para + "\n\n"
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # Добавляем перекрытие между чанками
        if overlap > 0 and len(chunks) > 1:
            overlapped_chunks = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_chunk = chunks[i-1]
                overlap_text = prev_chunk[-overlap:] if len(prev_chunk) > overlap else prev_chunk
                overlapped_chunks.append(overlap_text + " " + chunks[i])
            chunks = overlapped_chunks
        
        return chunks
    
    @staticmethod
    async def index_document(document_id: int) -> int:
        """
        Проиндексировать документ: разбить на чанки, получить эмбеддинги.
        
        Returns:
            Количество созданных чанков
        """
        async with async_session() as session:
            # Получаем документ
            result = await session.execute(
                select(Document).where(Document.id == document_id)
            )
            doc = result.scalar_one_or_none()
            
            if not doc:
                raise ValueError(f"Document {document_id} not found")
            
            # Удаляем старые чанки
            await session.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            
            # Разбиваем на чанки
            chunks_text = DocumentService.chunk_text(doc.content)
            
            if not chunks_text:
                doc.is_indexed = True
                doc.indexed_at = datetime.utcnow()
                doc.chunks_count = 0
                await session.commit()
                return 0
            
            print(f"  Индексация: {len(chunks_text)} чанков...")
            
            # Получаем эмбеддинги и сохраняем чанки
            for i, chunk_text in enumerate(chunks_text):
                embedding = await embedding_service.get_embedding(chunk_text)
                
                chunk = DocumentChunk(
                    document_id=doc.id,
                    tender_id=doc.tender_id,
                    chunk_index=i,
                    content=chunk_text,
                    embedding=embedding,
                    chunk_metadata={"chunk_number": i + 1, "total_chunks": len(chunks_text)}
                )
                session.add(chunk)
                
                # Логируем прогресс
                if (i + 1) % 3 == 0 or i == len(chunks_text) - 1:
                    print(f"    Обработано {i + 1}/{len(chunks_text)} чанков")
            
            # Обновляем статус документа
            doc.is_indexed = True
            doc.indexed_at = datetime.utcnow()
            doc.chunks_count = len(chunks_text)
            
            await session.commit()
            
            return len(chunks_text)
    
    @staticmethod
    async def search(
        query: str,
        tender_id: Optional[int] = None,
        top_k: int = None,
    ) -> List[dict]:
        """
        Семантический поиск с опциональной фильтрацией по тендеру.
        
        Returns:
            Список релевантных чанков с метаданными
        """
        top_k = top_k or settings.RAG_TOP_K
        
        async with async_session() as session:
            # Получаем эмбеддинг запроса
            query_embedding = await embedding_service.get_embedding(query)
            
            # Преобразуем список в строку формата pgvector: "[0.1, 0.2, ...]"
            query_embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"
            
            # Строим SQL-запрос с использованием pgvector
            # Используем CAST вместо :: для совместимости с SQLAlchemy text()
            if tender_id:
                # Поиск в контексте конкретного тендера
                sql = text("""
                    SELECT 
                        dc.id,
                        dc.document_id,
                        dc.tender_id,
                        dc.chunk_index,
                        dc.content,
                        dc.metadata,
                        d.title as document_title,
                        d.doc_type,
                        1 - (dc.embedding <=> CAST(:query_emb AS vector)) as similarity
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    WHERE dc.tender_id = :tender_id
                    ORDER BY dc.embedding <=> CAST(:query_emb AS vector)
                    LIMIT :top_k
                """)
                result = await session.execute(sql, {
                    "query_emb": query_embedding_str,
                    "tender_id": tender_id,
                    "top_k": top_k
                })
            else:
                # Поиск по всем тендерам
                sql = text("""
                    SELECT 
                        dc.id,
                        dc.document_id,
                        dc.tender_id,
                        dc.chunk_index,
                        dc.content,
                        dc.metadata,
                        d.title as document_title,
                        d.doc_type,
                        1 - (dc.embedding <=> CAST(:query_emb AS vector)) as similarity
                    FROM document_chunks dc
                    JOIN documents d ON dc.document_id = d.id
                    ORDER BY dc.embedding <=> CAST(:query_emb AS vector)
                    LIMIT :top_k
                """)
                result = await session.execute(sql, {
                    "query_emb": query_embedding_str,
                    "top_k": top_k
                })
            
            # Формируем результаты
            sources = []
            for row in result:
                sources.append({
                    "chunk_id": row[0],
                    "document_id": row[1],
                    "tender_id": row[2],
                    "chunk_index": row[3],
                    "content": row[4],
                    "metadata": row[5],
                    "document_title": row[6],
                    "doc_type": row[7],
                    "similarity": float(row[8])
                })
            
            return sources
    
    @staticmethod
    async def delete_document(document_id: int) -> bool:
        """Удалить документ и все его чанки."""
        async with async_session() as session:
            result = await session.execute(
                delete(Document).where(Document.id == document_id)
            )
            await session.commit()
            return result.rowcount > 0


# Глобальный экземпляр
document_service = DocumentService()