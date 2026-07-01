import asyncio
import httpx
import math
import time
from typing import List, Dict


async def get_embedding(client: httpx.AsyncClient, model: str, text: str) -> tuple:
    """Получить эмбеддинг и замерить время."""
    start = time.time()
    response = await client.post(
        "http://localhost:11434/api/embeddings",
        json={"model": model, "prompt": text},
        timeout=60
    )
    elapsed = (time.time() - start) * 1000
    
    if response.status_code != 200:
        raise Exception(f"Ошибка модели {model}: {response.status_code}\n{response.text}")
    
    embedding = response.json()["embedding"]
    return embedding, elapsed


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Косинусное сходство между двумя векторами."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    return dot_product / (norm_a * norm_b) if norm_a > 0 and norm_b > 0 else 0


async def test_model(client: httpx.AsyncClient, model: str, texts: Dict[str, str], query: str) -> Dict:
    """Протестировать одну модель."""
    print(f"\n{'='*70}")
    print(f"🔬 ТЕСТИРОВАНИЕ МОДЕЛИ: {model}")
    print(f"{'='*70}")
    
    # Получаем эмбеддинги для всех текстов
    embeddings = {}
    times = []
    
    for name, text in texts.items():
        emb, elapsed = await get_embedding(client, model, text)
        embeddings[name] = emb
        times.append(elapsed)
        print(f"  ✓ {name:15s}: {len(emb)} dims за {elapsed:.0f} мс")
    
    # Получаем эмбеддинг запроса
    query_emb, query_time = await get_embedding(client, model, query)
    print(f"  ✓ {'QUERY':15s}: {len(query_emb)} dims за {query_time:.0f} мс")
    
    # Вычисляем сходства
    similarities = []
    for name, emb in embeddings.items():
        sim = cosine_similarity(query_emb, emb)
        similarities.append((name, sim))
    
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    return {
        "model": model,
        "dimensions": len(query_emb),
        "avg_time_ms": sum(times) / len(times),
        "query_time_ms": query_time,
        "similarities": similarities,
        "embeddings": embeddings,
        "query_embedding": query_emb
    }


async def main():
    """Главная функция сравнения."""
    
    # Тестовые тексты
    texts = {
        "tender_1": "Выполнение работ по реконструкции автодороги Чегем II-Булунгу км 15-км 64,8 с мостом через р. Чаты-Су. НМЦК: 64 833 943,20 руб.",
        "tender_2": "Капитальный ремонт автодороги Чегем-Булунгу с устройством мостового перехода. Начальная цена контракта 64 миллиона рублей.",
        "spam_1": "Пополните аванс для публикации вакансий на Авито. Работодатели, которые не делают это вовремя, могут терять соискателей.",
        "spam_2": "Скидка 50% на мебель! Только сегодня! Успейте воспользоваться специальным предложением. Звоните 8-800-100-31-32.",
        "general_1": "Добрый день! Подтверждаю встречу на понедельник в 14:00. Повестку отправлю позже. С уважением, Иван.",
        "technical": "Бетон марки М400 должен соответствовать ГОСТ 7473-2010. Подвижность П3, морозостойкость F200, водонепроницаемость W6.",
    }
    
    # Тестовые запросы
    queries = [
        "Какая сумма контракта на реконструкцию автодороги?",
        "Какие сроки выполнения работ?",
        "Что требуется от участников закупки?",
    ]
    
    # ⚠️ ВАЖНО: Используйте имена моделей из вывода `ollama list`
    models = [
        "bge-m3",
        "jeffh/intfloat-multilingual-e5-large-instruct:q8_0",
    ]
    
    print("=" * 70)
    print("📊 СРАВНЕНИЕ МОДЕЛЕЙ ЭМБЕДДИНГОВ")
    print("=" * 70)
    
    async with httpx.AsyncClient() as client:
        results = {}
        
        # Тестируем каждую модель
        for model in models:
            try:
                result = await test_model(client, model, texts, queries[0])
                results[model] = result
            except Exception as e:
                print(f"\n✗ Ошибка тестирования модели {model}: {e}")
                continue
        
        if len(results) < 2:
            print("\n⚠️ Не удалось протестировать обе модели. Проверьте имена через `ollama list`")
            return
        
        # Итоговая таблица сравнения
        print("\n" + "=" * 70)
        print("📈 СРАВНИТЕЛЬНАЯ ТАБЛИЦА")
        print("=" * 70)
        
        bge_model = "bge-m3"
        e5_model = "jeffh/intfloat-multilingual-e5-large-instruct:q8_0"
        
        bge = results[bge_model]
        e5 = results[e5_model]
        
        print(f"\n{'Параметр':<30} {'bge-m3':<20} {'e5-large':<20}")
        print("-" * 70)
        print(f"{'Размерность эмбеддинга':<30} {bge['dimensions']:<20} {e5['dimensions']:<20}")
        print(f"{'Среднее время (мс)':<30} {bge['avg_time_ms']:<20.1f} {e5['avg_time_ms']:<20.1f}")
        print(f"{'Время запроса (мс)':<30} {bge['query_time_ms']:<20.1f} {e5['query_time_ms']:<20.1f}")
        
        # Качество ранжирования для запроса 1
        print(f"\n{'🔍 Запрос: \"Какая сумма контракта...\"':<70}")
        print("-" * 70)
        print(f"{'Документ':<20} {'bge-m3':<15} {'e5-large':<15} {'Победитель':<15}")
        print("-" * 70)
        
        bge_dict = {name: sim for name, sim in bge["similarities"]}
        e5_dict = {name: sim for name, sim in e5["similarities"]}
        
        all_docs = set(bge_dict.keys()) | set(e5_dict.keys())
        
        bge_wins = 0
        e5_wins = 0
        
        for doc in sorted(all_docs):
            bge_sim = bge_dict.get(doc, 0)
            e5_sim = e5_dict.get(doc, 0)
            
            if bge_sim > e5_sim:
                winner = "bge-m3 ✓"
                bge_wins += 1
            elif e5_sim > bge_sim:
                winner = "e5-large ✓"
                e5_wins += 1
            else:
                winner = "ничья"
            
            print(f"{doc:<20} {bge_sim:<15.4f} {e5_sim:<15.4f} {winner:<15}")
        
        # Топ-3 для каждой модели
        print(f"\n{'🏆 ТОП-3 ДОКУМЕНТА ДЛЯ ЗАПРОСА':<70}")
        print("-" * 70)
        
        print(f"\nbge-m3:")
        for i, (name, sim) in enumerate(bge["similarities"][:3], 1):
            print(f"  {i}. {name:<20} {sim:.4f}")
        
        print(f"\nintfloat/multilingual-e5-large:")
        for i, (name, sim) in enumerate(e5["similarities"][:3], 1):
            print(f"  {i}. {name:<20} {sim:.4f}")
        
        # Дополнительные запросы
        print(f"\n{'🔍 ДОПОЛНИТЕЛЬНЫЕ ЗАПРОСЫ':<70}")
        print("-" * 70)
        
        for query in queries[1:]:
            print(f"\nЗапрос: \"{query}\"")
            
            query_emb_bge, _ = await get_embedding(client, bge_model, query)
            query_emb_e5, _ = await get_embedding(client, e5_model, query)
            
            bge_sims = [(name, cosine_similarity(query_emb_bge, emb)) 
                        for name, emb in bge["embeddings"].items()]
            e5_sims = [(name, cosine_similarity(query_emb_e5, emb)) 
                       for name, emb in e5["embeddings"].items()]
            
            bge_sims.sort(key=lambda x: x[1], reverse=True)
            e5_sims.sort(key=lambda x: x[1], reverse=True)
            
            print(f"  bge-m3  топ-1: {bge_sims[0][0]:<20} ({bge_sims[0][1]:.4f})")
            print(f"  e5-large топ-1: {e5_sims[0][0]:<20} ({e5_sims[0][1]:.4f})")
            
            # Подсчет побед для этого запроса
            if bge_sims[0][0].startswith("tender_"):
                bge_wins += 1
            if e5_sims[0][0].startswith("tender_"):
                e5_wins += 1
        
        # Итоговая рекомендация
        print("\n" + "=" * 70)
        print("💡 РЕКОМЕНДАЦИЯ")
        print("=" * 70)
        
        print(f"\nbge-m3 побед: {bge_wins}")
        print(f"e5-large побед: {e5_wins}")
        
        if bge_wins > e5_wins:
            print("\n✅ РЕКОМЕНДУЕТСЯ: bge-m3")
            print("   - Лучше качество для русского языка")
            print("   - Меньше размер модели (568 MB vs 1.2 GB)")
            print("   - Быстрее работает")
            print("   - Поддерживает гибридный поиск (dense + sparse)")
        elif e5_wins > bge_wins:
            print("\n✅ РЕКОМЕНДУЕТСЯ: jeffh/intfloat-multilingual-e5-large-instruct")
            print("   - Лучше качество для мультilingual поиска")
            print("   - Проверенная модель для RAG")
        else:
            print("\n⚠️ МОДЕЛИ ПОКАЗАЛИ ОДИНАКОВЫЙ РЕЗУЛЬТАТ")
            print("   Рекомендуется bge-m3 из-за меньшего размера и гибкости")


if __name__ == "__main__":
    asyncio.run(main())