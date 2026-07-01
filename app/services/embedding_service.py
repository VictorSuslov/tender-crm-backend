import httpx
from typing import List
from app.config import settings


class EmbeddingService:
    """Сервис для работы с эмбеддингами через Ollama."""
    
    def __init__(self):
        self.api_url = "http://localhost:11434/api/embeddings"
        self.model = settings.EMBEDDING_MODEL_NAME
        self.dimensions = settings.EMBEDDING_DIMENSIONS
    
    async def get_embedding(self, text: str) -> List[float]:
        """Получить эмбеддинг для одного текста."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=60
            )
            response.raise_for_status()
            return response.json()["embedding"]
    
    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Получить эмбеддинги для списка текстов."""
        embeddings = []
        for text in texts:
            embedding = await self.get_embedding(text)
            embeddings.append(embedding)
        return embeddings


# Глобальный экземпляр
embedding_service = EmbeddingService()