import asyncio
import httpx
import math

async def test_bge():
    async with httpx.AsyncClient() as client:
        texts = {
            "tender_1": "Выполнение работ по реконструкции автодороги Чегем II-Булунгу. НМЦК 64 млн руб.",
            "spam_1": "Пополните аванс для публикации вакансий на Авито.",
        }
        
        print("Тест модели bge-m3...")
        embeddings = {}
        
        for name, text in texts.items():
            resp = await client.post(
                "http://localhost:11434/api/embeddings",
                json={"model": "bge-m3", "prompt": text},
                timeout=60
            )
            emb = resp.json()["embedding"]
            embeddings[name] = emb
            print(f"✓ {name}: получен вектор ({len(emb)} dims)")
            
        # Проверка запроса
        query = "Какая цена контракта на дорогу?"
        resp = await client.post(
            "http://localhost:11434/api/embeddings",
            json={"model": "bge-m3", "prompt": query},
            timeout=60
        )
        q_emb = resp.json()["embedding"]
        
        def cosine_sim(a, b):
            return sum(x*y for x,y in zip(a,b)) / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(x*x for x in b)))
            
        sim_1 = cosine_sim(q_emb, embeddings["tender_1"])
        sim_2 = cosine_sim(q_emb, embeddings["spam_1"])
        
        print(f"\nЗапрос: '{query}'")
        print(f"Сходство с тендером: {sim_1:.4f}")
        print(f"Сходство со спамом: {sim_2:.4f}")
        
        if sim_1 > sim_2:
            print("\n✅ Отлично! Тендер выше спама.")
        else:
            print("\n⚠️ Нужно проверить настройки.")

if __name__ == "__main__":
    asyncio.run(test_bge())