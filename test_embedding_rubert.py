import asyncio
import time
from sentence_transformers import SentenceTransformer
import numpy as np

def test_rubert():
    """Тест русской модели эмбеддингов."""
    print("=" * 70)
    print("ТЕСТ РУССКОЙ МОДЕЛИ ЭМБЕДДИНГОВ (rubert-tiny2)")
    print("=" * 70)
    
    # Загрузка модели (при первом запуске скачается)
    print("\nЗагрузка модели cointegrated/rubert-tiny2...")
    start = time.time()
    model = SentenceTransformer('cointegrated/rubert-tiny2')
    print(f"✓ Модель загружена за {time.time() - start:.2f} сек")
    print(f"  Размерность эмбеддинга: {model.get_sentence_embedding_dimension()}")
    
    # Тестовые тексты
    texts = {
        "tender_1": "Выполнение работ по реконструкции автодороги Чегем II-Булунгу км 15-км 64,8 с мостом через р. Чаты-Су. НМЦК: 64 833 943,20 руб.",
        "tender_2": "Капитальный ремонт автодороги Чегем-Булунгу с устройством мостового перехода. Начальная цена контракта 64 миллиона рублей.",
        "spam_1": "Пополните аванс для публикации вакансий на Авито. Работодатели, которые не делают это вовремя, могут терять соискателей.",
        "spam_2": "Скидка 50% на мебель! Только сегодня! Успейте воспользоваться специальным предложением. Звоните 8-800-100-31-32.",
        "general_1": "Добрый день! Подтверждаю встречу на понедельник в 14:00. Повестку отправлю позже. С уважением, Иван.",
        "technical": "Бетон марки М400 должен соответствовать ГОСТ 7473-2010. Подвижность П3, морозостойкость F200, водонепроницаемость W6.",
    }
    
    print("\n" + "=" * 70)
    print("ГЕНЕРАЦИЯ ЭМБЕДДИНГОВ")
    print("=" * 70)
    
    # Получаем эмбеддинги
    embeddings = {}
    for name, text in texts.items():
        start = time.time()
        embedding = model.encode(text)
        elapsed = (time.time() - start) * 1000
        embeddings[name] = embedding
        print(f"✓ {name:12s}: {len(embedding)} dims за {elapsed:.1f} мс")
    
    # Запрос
    query = "Какая сумма контракта на реконструкцию автодороги?"
    query_emb = model.encode(query)
    
    print("\n" + "=" * 70)
    print(f"🔍 ЗАПРОС: \"{query}\"")
    print("=" * 70)
    
    # Косинусное сходство
    def cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
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
    print(f"✓ Разница между топ-1 и топ-2: {top1[1] - top2[1]:.4f}")
    
    # Проверяем, что тендерные документы в топе
    tender_in_top2 = any(name.startswith("tender_") for name, _ in similarities[:2])
    spam_not_top = not similarities[0][0].startswith("spam_")
    
    if tender_in_top2 and spam_not_top:
        print("\n✅ МОДЕЛЬ РАБОТАЕТ ОТЛИЧНО!")
        print("   Тендерные документы правильно находятся по запросу о НМЦК.")
        print("   Спам не попадает в топ результатов.")
    else:
        print("\n⚠️ Модель работает, но можно улучшить.")

if __name__ == "__main__":
    test_rubert()