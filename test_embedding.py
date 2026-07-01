import asyncio
import httpx
import math

async def test_embedding():
    """Тест получения эмбеддинга от Ollama."""
    async with httpx.AsyncClient() as client:
        # Тестовые тексты
        text1 = "Выполнение работ по реконструкции автодороги Чегем II-Булунгу"
        text2 = "Капитальный ремонт автодороги Чегем-Булунгу с мостом"
        text3 = "Пополните аванс для публикации вакансий на Авито"
        
        print("=" * 60)
        print("ТЕСТ МОДЕЛИ ЭМБЕДДИНГОВ (nomic-embed-text)")
        print("=" * 60)
        
        # Получаем эмбеддинги
        embeddings = []
        for i, text in enumerate([text1, text2, text3], 1):
            print(f"\nТекст {i}: {text}")
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "nomic-embed-text", "prompt": text},
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"✗ Ошибка: {response.status_code}")
                print(response.text)
                return
            
            result = response.json()
            embedding = result["embedding"]
            embeddings.append(embedding)
            
            print(f"✓ Размер: {len(embedding)}")
            print(f"  Первые 5 значений: {[round(x, 4) for x in embedding[:5]]}")
        
        # Косинусное сходство
        def cosine_similarity(a, b):
            dot_product = sum(x*y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x*x for x in a))
            norm_b = math.sqrt(sum(x*x for x in b))
            return dot_product / (norm_a * norm_b)
        
        print("\n" + "=" * 60)
        print("КОСИНУСНОЕ СХОДСТВО:")
        print("=" * 60)
        
        sim_12 = cosine_similarity(embeddings[0], embeddings[1])
        sim_13 = cosine_similarity(embeddings[0], embeddings[2])
        sim_23 = cosine_similarity(embeddings[1], embeddings[2])
        
        print(f"\nТекст 1 vs Текст 2 (похожие тендеры): {sim_12:.4f}")
        print(f"Текст 1 vs Текст 3 (тендер vs спам):   {sim_13:.4f}")
        print(f"Текст 2 vs Текст 3 (тендер vs спам):   {sim_23:.4f}")
        
        print("\n" + "=" * 60)
        if sim_12 > 0.7 and sim_13 < 0.5:
            print("✓ Модель работает корректно!")
            print("  Похожие тексты имеют высокое сходство.")
            print("  Разные тексты имеют низкое сходство.")
        else:
            print("⚠ Модель работает, но результаты неожиданные.")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_embedding())