import asyncio
import httpx
import time


API_URL = "http://localhost:8000"


async def test_api():
    """Тест API endpoints для RAG."""
    async with httpx.AsyncClient(timeout=60) as client:
        print("=" * 70)
        print("ТЕСТ RAG API")
        print("=" * 70)
        
        # Получаем список тендеров
        print("\n[1/7] Получение списка тендеров...")
        response = await client.get(f"{API_URL}/api/tenders/")
        if response.status_code != 200:
            print(f"✗ Ошибка: {response.status_code}")
            return
        tenders = response.json()
        if not tenders["items"]:
            print("✗ Нет тендеров в БД")
            return
        tender_id = tenders["items"][0]["id"]
        print(f"✓ Используем тендер ID={tender_id}: {tenders['items'][0]['purchase_name'][:60]}")
        
        # Создаем документ
        print("\n[2/7] Создание документа...")
        response = await client.post(
            f"{API_URL}/api/documents/tenders/{tender_id}",
            json={
                "doc_type": "NOTE",
                "title": "Тестовая заметка для RAG",
                "content": """
                НМЦК контракта составляет 64 833 943,20 рублей.
                Срок выполнения работ: 120 дней с даты заключения контракта.
                Начало работ не позднее 30 дней с даты подписания.
                Окончание работ до 31.12.2026.
                Гарантийный срок: 5 лет.
                """
            }
        )
        if response.status_code != 201:
            print(f"✗ Ошибка: {response.status_code} - {response.text}")
            return
        doc = response.json()
        doc_id = doc["id"]
        print(f"✓ Документ создан: ID={doc_id}")
        
        # Индексируем документ
        print("\n[3/7] Индексация документа...")
        start = time.time()
        response = await client.post(f"{API_URL}/api/documents/{doc_id}/index")
        elapsed = int((time.time() - start) * 1000)
        if response.status_code != 200:
            print(f"✗ Ошибка: {response.status_code} - {response.text}")
            return
        result = response.json()
        print(f"✓ Индексация завершена: {result['chunks_count']} чанков за {elapsed} мс")
        
        # Семантический поиск
        print("\n[4/7] Семантический поиск...")
        queries = ["Какая НМЦК?", "Какие сроки?", "Гарантийный срок"]
        for query in queries:
            response = await client.post(
                f"{API_URL}/api/documents/search",
                params={"query": query, "tender_id": tender_id, "top_k": 2}
            )
            if response.status_code == 200:
                result = response.json()
                print(f"\n🔍 Запрос: \"{query}\"")
                for i, chunk in enumerate(result["chunks"][:2], 1):
                    print(f"  {i}. [Сходство: {chunk['similarity']:.4f}] {chunk['content'][:80]}...")
            else:
                print(f"✗ Ошибка поиска: {response.status_code}")
        
        # RAG-запрос
        print("\n[5/7] RAG-запрос...")
        response = await client.post(
            f"{API_URL}/api/rag/query",
            json={
                "question": "Какая сумма контракта и какие сроки выполнения?",
                "tender_id": tender_id,
                "top_k": 5
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"\n💬 Ответ:")
            print("-" * 70)
            print(result["answer"])
            print("-" * 70)
            print(f"⏱ Время: {result['processing_time_ms']} мс")
            print(f"📚 Источников: {len(result['sources'])}")
        else:
            print(f"✗ Ошибка RAG: {response.status_code} - {response.text}")
        
        # История запросов
        print("\n[6/7] История запросов...")
        response = await client.get(f"{API_URL}/api/rag/history")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Всего запросов в истории: {result['total']}")
            for item in result["items"][:3]:
                print(f"  - [{item['created_at'][:19]}] {item['query'][:50]}...")
        else:
            print(f"✗ Ошибка: {response.status_code}")
        
        # Статистика
        print("\n[7/7] Статистика...")
        response = await client.get(f"{API_URL}/api/documents/statistics/overview")
        if response.status_code == 200:
            stats = response.json()
            print(f"✓ Документов: {stats['total_documents']}")
            print(f"  Индексировано: {stats['indexed_documents']}")
            print(f"  Всего чанков: {stats['total_chunks']}")
            print(f"  По типам: {stats['by_type']}")
        else:
            print(f"✗ Ошибка: {response.status_code}")
        
        print("\n" + "=" * 70)
        print("✓ ТЕСТ ЗАВЕРШЕН")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_api())