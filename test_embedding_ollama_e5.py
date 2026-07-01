import asyncio
import httpx
import math

async def test_embedding():
    """Тест модели intfloat/multilingual-e5-large через Ollama."""
    async with httpx.AsyncClient() as client:
        
        # Тестовые тексты
        texts = {
            "tender_1": "Выполнение работ по реконструкции автодороги Чегем II-Булунгу км 15-км 64,8 с мостом через р. Чаты-Су. НМЦК: 64 833 943,20 руб.",
            "tender_2": "Капитальный ремонт автодороги Чегем-Булунгу с устройством мостового перехода. Начальная цена контракта 64 миллиона рублей.",
            "spam_1": "Пополните аванс для публикации вакансий на Авито. Работодатели, которые не делают это вовремя, могут терять соискателей.",
            "spam_2": "Скидка 50% на мебель! Только сегодня! Успейте воспользоваться специальным предложением. Звоните 8-800-100-31-32.",
            "general_1": "Добрый день! Подтверждаю встречу на понедельник в 14:00. Повестку отправлю позже. С уважением, Иван.",
            "technical": "Бетон марки М400 должен соответствовать ГОСТ 7473-2010. Подвижность П3, морозостойкость F200, водонепроницаемость W6.",
        }
        
        print("=" * 70)
        print("ТЕСТ МОДЕЛИ jeffh/intfloat-multilingual-e5-large-instruct (через Ollama)")
        print("=" * 70)
        
        # Получаем эмбеддинги
        embeddings = {}
        for name, text in texts.items():
            print(f"\nОбработка: {name}")
            response = await client.post(
                "http://localhost:11434/api/embeddings",
                json={
                    "model": "jeffh/intfloat-multilingual-e5-large-instruct:q8_0",
                    "prompt": text
                },
                timeout=60
            )
            
            if response.status_code != 200:
                print(f"✗ Ошибка: {response.status_code}")
                print(response.text)
                return
            
            result = response.json()
            embedding = result["embedding"]
            embeddings[name] = embedding
            
            print(f"✓ Размер: {len(embedding)} dims")
        
        # Запрос
        query = "Какая сумма контракта на реконструкцию автодороги?"
        print(f"\n🔍 Запрос: \"{query}\"")
        
        response = await client.post(
            "http://localhost:11434/api/embeddings",
            json={
                "model": "jeffh/intfloat-multilingual-e5-large-instruct:q8_0",
                "prompt": query
            },
            timeout=60
        )
        query_emb = response.json()["embedding"]
        
        print(f"✓ Размер эмбеддинга запроса: {len(query_emb)} dims")
        
        # Косинусное сходство
        def cosine_similarity(a, b):
            dot_product = sum(x*y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x*x for x in a))
            norm_b = math.sqrt(sum(x*x for x in b))
            return dot_product / (norm_a * norm_b)
        
        print("\n" + "=" * 70)
        print("РЕЗУЛЬТАТЫ ПОИСКА")
        print("=" * 70)
        
        # Сортируем по сходству с запросом
        similarities = []
        for name, emb in embeddings.items():
            sim = cosine_similarity(query_emb, emb)
            similarities.append((name, sim))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        for name, sim in similarities:
            bar = "█" * int(sim * 30)
            emoji = "✅" if sim > 0.75 else "⚠️" if sim > 0.65 else "❌"
            print(f"  {emoji} {name:12s}: {sim:.4f} {bar}")
        
        print("\n" + "=" * 70)
        print("ВЫВОД:")
        print("=" * 70)
        
        top1 = similarities[0]
        top2 = similarities[1]
        
        print(f"\n✓ Топ-1 результат: {top1[0]} (сходство {top1[1]:.4f})")
        print(f"✓ Топ-2 результат: {top2[0]} (сходство {top2[1]:.4f})")
        
        # Проверяем, что тендерные документы в топе
        tender_in_top2 = any(name.startswith("tender_") for name, _ in similarities[:2])
        spam_not_top = not similarities[0][0].startswith("spam_")
        
        if tender_in_top2 and spam_not_top:
            print("\n✅ МОДЕЛЬ РАБОТАЕТ ОТЛИЧНО!")
            print("   Тендерные документы правильно находятся по запросу о НМЦК.")
            print("   Спам не попадает в топ результатов.")
        else:
            print("\n⚠️ Модель работает, но результаты неожиданные.")

if __name__ == "__main__":
    asyncio.run(test_embedding())