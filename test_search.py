import httpx


def test_search():
    print("Тест семантического поиска...")
    print("=" * 60)
    
    with httpx.Client(timeout=30.0) as client:
        # Проверяем статистику
        print("\n[1/3] Проверка наличия чанков...")
        response = client.get("http://localhost:8000/api/documents/statistics/overview")
        if response.status_code == 200:
            stats = response.json()
            print(f"  Всего документов: {stats.get('total_documents', 0)}")
            print(f"  Индексировано: {stats.get('indexed_documents', 0)}")
            print(f"  Всего чанков: {stats.get('total_chunks', 0)}")
            
            if stats.get('total_chunks', 0) == 0:
                print("  ✗ Нет чанков в БД!")
                return
        else:
            print(f"  ✗ Ошибка: {response.status_code}")
            return
        
        # Тестируем поиск
        print("\n[2/3] Поиск: 'Какая НМЦК контракта?'...")
        response = client.post(
            "http://localhost:8000/api/documents/search",
            params={
                "query": "Какая НМЦК контракта?",
                "top_k": 5
            }
        )
        
        print(f"  Статус: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            chunks = result.get("chunks", [])
            print(f"  Найдено чанков: {len(chunks)}")
            
            if chunks:
                print(f"\n[3/3] Результаты:")
                for i, chunk in enumerate(chunks, 1):
                    print(f"\n  Чанк {i}:")
                    print(f"    Документ: {chunk.get('document_title', 'N/A')}")
                    print(f"    Similarity: {chunk.get('similarity', 0):.4f}")
                    print(f"    Содержимое: {chunk.get('content', '')[:200]}...")
            else:
                print("  ✗ Ничего не найдено")
        else:
            print(f"  ✗ Ошибка: {response.text}")


if __name__ == "__main__":
    test_search()