import asyncio
from app.services.document_service import document_service
from app.services.rag_service import rag_service
from app.database import async_session
from app.models.tender import Tender


async def test_rag():
    """Тест RAG-системы."""
    print("=" * 70)
    print("ТЕСТ RAG-СИСТЕМЫ")
    print("=" * 70)
    
    # Шаг 0: Создаем тестовый тендер
    print("\n[0/5] Создание тестового тендера...")
    async with async_session() as session:
        tender = Tender(
            purchase_name="Выполнение работ по реконструкции автодороги Чегем II-Булунгу",
            customer_name="МУНИЦИПАЛЬНОЕ КАЗЕННОЕ УЧРЕЖДЕНИЕ \"УПРАВЛЕНИЕ КАПИТАЛЬНОГО СТРОИТЕЛЬСТВА\"",
            nmck=64833943.20,
            currency="RUB",
            status="NEW",
            notes="Тестовый тендер для RAG"
        )
        session.add(tender)
        await session.commit()
        await session.refresh(tender)
        tender_id = tender.id
    
    print(f"✓ Тендер создан: ID={tender_id}")
    
    # Тест 1: Создание тестового документа
    print("\n[1/5] Создание тестового документа...")
    
    doc = await document_service.create_document(
        tender_id=tender_id,
        doc_type="TENDER_APPLICATION",
        title="Тестовая заявка на участие в тендере",
        content="""
        Раздел 1. Общие сведения
        
        Заказчик: МУНИЦИПАЛЬНОЕ КАЗЕННОЕ УЧРЕЖДЕНИЕ "УПРАВЛЕНИЕ КАПИТАЛЬНОГО СТРОИТЕЛЬСТВА"
        Местная администрация городского округа Нальчик
        
        Раздел 2. Технические требования
        
        Необходимо выполнить работы по реконструкции автодороги Чегем II-Булунгу 
        км 15-км 64,8 с мостом через р. Чаты-Су.
        
        Технические характеристики:
        - Длина участка: 49,8 км
        - Ширина проезжей части: 7 метров
        - Количество полос: 2
        - Тип покрытия: асфальтобетон
        
        Раздел 3. Финансовые условия
        
        НМЦК: 64 833 943,20 руб.
        Валюта: Российский рубль.
        Источник финансирования: бюджет КБР.
        Порядок оплаты: аванс 30%, остаток по факту выполненных работ.
        
        Раздел 4. Сроки выполнения
        
        Срок выполнения работ: 120 дней с даты заключения контракта.
        Начало работ: не позднее 30 дней с даты подписания контракта.
        Окончание работ: до 31.12.2026.
        Гарантийный срок: 5 лет.
        
        Раздел 5. Требования к участникам
        
        Опыт выполнения аналогичных работ не менее 3 лет.
        Наличие специализированной техники:
        - Асфальтоукладчик
        - Каток дорожный
        - Автогрейдер
        - Самосвалы (не менее 5 единиц)
        
        Наличие действующей лицензии СРО.
        Отсутствие задолженностей перед бюджетом.
        
        Раздел 6. Обеспечение заявки
        
        Размер обеспечения: 648 339,43 руб. (1% от НМЦК).
        Форма обеспечения: банковская гарантия или денежные средства.
        
        Раздел 7. Критерии оценки
        
        Цена контракта: 60%
        Качество работ: 25%
        Срок выполнения: 15%
        """,
        metadata={"test": True, "version": "1.0"}
    )
    
    print(f"✓ Документ создан: ID={doc.id}")
    
    # Тест 2: Индексация документа
    print("\n[2/5] Индексация документа...")
    chunks_count = await document_service.index_document(doc.id)
    print(f"✓ Документ проиндексирован: {chunks_count} чанков")
    
    # Тест 3: Тест поиска
    print("\n[3/5] Тест поиска...")
    
    queries = [
        "Какая НМЦК контракта?",
        "Какие сроки выполнения работ?",
        "Какие требования к участникам?",
        "Кто заказчик?",
        "Какой размер обеспечения заявки?",
    ]
    
    for query in queries:
        print(f"\n🔍 Запрос: \"{query}\"")
        results = await document_service.search(query, tender_id=tender_id, top_k=2)
        
        for i, result in enumerate(results, 1):
            content_preview = result['content'][:100].replace('\n', ' ')
            print(f"  {i}. [Сходство: {result['similarity']:.4f}] {content_preview}...")
    
    # Тест 4: RAG-запрос
    print("\n[4/5] Тест RAG-запроса...")
    
    rag_query = "Какая сумма контракта и какие сроки выполнения работ?"
    print(f"\n🤖 Вопрос: \"{rag_query}\"")
    
    result = await rag_service.query(
        question=rag_query,
        tender_id=tender_id,
        top_k=5
    )
    
    print(f"\n💬 Ответ LLM:")
    print("-" * 70)
    print(result['answer'])
    print("-" * 70)
    print(f"\n⏱ Время обработки: {result['processing_time_ms']} мс")
    print(f"📚 Использовано источников: {len(result['sources'])}")
    
    # Тест 5: Глобальный поиск (без фильтра по тендеру)
    print("\n[5/5] Тест глобального поиска...")
    
    global_query = "Какие требования к участникам закупки?"
    print(f"\n🔍 Глобальный запрос: \"{global_query}\"")
    
    results = await document_service.search(global_query, top_k=3)
    
    for i, result in enumerate(results, 1):
        print(f"\n  {i}. [Тендер #{result['tender_id']}, Сходство: {result['similarity']:.4f}]")
        print(f"     Документ: {result['document_title']}")
        print(f"     {result['content'][:150]}...")
    
    print("\n" + "=" * 70)
    print("✓ ТЕСТ ЗАВЕРШЕН")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(test_rag())