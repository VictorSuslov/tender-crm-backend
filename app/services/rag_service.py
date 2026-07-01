import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import select, text

from app.database import async_session
from app.models.rag_query import RagQuery
from app.services.document_service import document_service
from app.services.llm_analyzer import LLMAnalyzer
from app.models.rag_query import RagQuery

class RAGService:
    """Сервис для RAG-поиска и генерации ответов."""
    
    def __init__(self):
        self.llm = LLMAnalyzer()
    
    async def query(
        self,
        question: str,
        tender_id: Optional[int] = None,
        top_k: int = 5,
        user_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Ответить на вопрос с использованием RAG.
        
        Args:
            question: Вопрос пользователя
            tender_id: Опциональный ID тендера для фильтрации
            top_k: Количество релевантных чанков
            user_id: ID пользователя (для истории)
        
        Returns:
            {
                "answer": "ответ LLM",
                "sources": [список релевантных документов],
                "processing_time_ms": время обработки
            }
        """
        start_time = time.time()
        
        try:
            # 1. Поиск релевантных чанков
            chunks = await document_service.search(question, tender_id, top_k)
            
            if not chunks:
                return {
                    "answer": "Не удалось найти релевантную информацию в документации.",
                    "sources": [],
                    "processing_time_ms": int((time.time() - start_time) * 1000)
                }
            
            # 2. Формирование контекста
            context = self._build_context(chunks)
            
            # 3. Запрос к LLM с контекстом
            answer = await self._generate_answer(question, context)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # 4. Сохранение в историю
            await self._save_query(
                user_id=user_id,
                tender_id=tender_id,
                query=question,
                answer=answer,
                sources=chunks,
                processing_time_ms=processing_time
            )
            
            return {
                "answer": answer,
                "sources": chunks,
                "processing_time_ms": processing_time
            }
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return {
                "answer": f"Ошибка при обработке запроса: {str(e)}",
                "sources": [],
                "processing_time_ms": processing_time,
                "error": str(e)
            }
    
    def _build_context(self, chunks: List[dict]) -> str:
        """Формирует контекст из найденных чанков."""
        context_parts = []
        
        for i, chunk in enumerate(chunks, 1):
            source_info = f"[Источник {i}: {chunk['document_title']}]"
            context_parts.append(f"{source_info}\n{chunk['content']}")
        
        return "\n\n---\n\n".join(context_parts)
    
    async def _generate_answer(self, question: str, context: str) -> str:
        """Генерирует ответ LLM на основе контекста."""
        prompt = f"""Ты - ассистент для работы с тендерной документацией.

Отвечай СТРОГО на русском языке.

Используй ТОЛЬКО информацию из предоставленного контекста.
Если в контексте нет ответа на вопрос - честно скажи об этом.
Указывай источники информации, когда это возможно.

КОНТЕКСТ ИЗ ДОКУМЕНТАЦИИ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}

ОТВЕТ (на русском языке, с указанием источников):"""

        # Используем существующий LLM-анализатор
        import httpx
        import json
        from app.config import settings
        
        payload = {
            "model": settings.OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    settings.OLLAMA_API_URL,
                    json=payload,
                    timeout=120
                )
                response.raise_for_status()
                result = response.json()
                return result.get("response", "Не удалось получить ответ.")
        except Exception as e:
            return f"Ошибка генерации ответа: {str(e)}"
    
    async def _save_query(
        self,
        user_id: Optional[int],
        tender_id: Optional[int],
        query: str,
        answer: str,
        sources: List[dict],
        processing_time_ms: int
    ):
        """Сохраняет запрос в историю."""
        async with async_session() as session:
            try:
                rag_query = RagQuery(
                    user_id=user_id,
                    tender_id=tender_id,
                    query=query,
                    answer=answer,
                    sources_count=len(sources),
                    sources=[{
                        "document_id": s["document_id"],
                        "document_title": s["document_title"],
                        "similarity": s["similarity"]
                    } for s in sources],
                    processing_time_ms=processing_time_ms
                )
                session.add(rag_query)
                await session.commit()
            except Exception as e:
                print(f"⚠ Не удалось сохранить запрос в историю: {e}")
    
    async def get_query_history(
        self,
        tender_id: Optional[int] = None,
        limit: int = 20
    ) -> List[dict]:
        """Получить историю запросов."""
        # TODO: реализовать после создания модели RagQuery
        return []


# Глобальный экземпляр
rag_service = RAGService()