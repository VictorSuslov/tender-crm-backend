import httpx
import sys


def test_upload():
    """Тест загрузки файла для тендера."""
    tender_id = 1  # Замените на реальный ID тендера
    
    # Создаём тестовый файл
    with open("test_document.txt", "w", encoding="utf-8") as f:
        f.write("Это тестовый документ для проверки индексации.\n")
        f.write("НМЦК контракта составляет 10 000 000 рублей.\n")
        f.write("Срок подачи заявок до 01.08.2026.\n")
    
    print(f"Тест загрузки файла для тендера ID={tender_id}")
    print("=" * 60)
    
    try:
        # Синхронный клиент (проще для отладки)
        with httpx.Client(timeout=30.0) as client:
            # Сначала проверяем, что сервер отвечает
            print("\n[1/3] Проверка сервера...")
            try:
                response = client.get("http://localhost:8000/api/tenders/?per_page=1")
                if response.status_code == 200:
                    print("  ✓ Сервер отвечает")
                else:
                    print(f"  ✗ Сервер вернул статус {response.status_code}")
                    return
            except Exception as e:
                print(f"  ✗ Сервер не отвечает: {e}")
                print("  → Убедитесь, что FastAPI запущен: python -m app.main")
                return
            
            # Загружаем файл
            print(f"\n[2/3] Загрузка файла test_document.txt...")
            with open("test_document.txt", "rb") as f:
                files = {"files": ("test_document.txt", f, "text/plain")}
                response = client.post(
                    f"http://localhost:8000/api/documents/upload/{tender_id}",
                    files=files
                )
            
            print(f"  Статус: {response.status_code}")
            
            if response.status_code == 200:
                print("  ✓ Файл загружен успешно")
                result = response.json()
                print(f"\n[3/3] Результат:")
                print(f"  Загружено документов: {result.get('uploaded_count', 0)}")
                
                for doc in result.get("documents", []):
                    print(f"  - ID: {doc.get('id')}")
                    print(f"    Имя: {doc.get('filename')}")
                    print(f"    Размер: {doc.get('size_bytes')} байт")
                    print(f"    Проиндексирован: {doc.get('is_indexed')}")
            else:
                print(f"  ✗ Ошибка загрузки")
                print(f"  Ответ: {response.text}")
    
    except httpx.TimeoutException:
        print("\n✗ Таймаут запроса (30 секунд)")
        print("→ Сервер слишком долго отвечает. Проверьте логи FastAPI.")
    except Exception as e:
        print(f"\n✗ Непредвиденная ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_upload()