import imaplib
import socket
import ssl
from datetime import datetime


def test_imap_connection(server, login, password, port=993):
    """
    Полная диагностика IMAP-подключения.
    
    Проверяет:
    1. DNS-резолвинг
    2. TCP-соединение
    3. SSL/TLS
    4. IMAP-протокол
    5. Аутентификация
    6. Выбор папки
    7. Получение писем
    """
    print("=" * 70)
    print(f"ДИАГНОСТИКА IMAP-ПОДКЛЮЧЕНИЯ")
    print(f"Сервер: {server}:{port}")
    print(f"Логин: {login}")
    print(f"Время: {datetime.now()}")
    print("=" * 70)
    
    # Шаг 1: DNS
    print("\n[1/7] Проверка DNS...")
    try:
        ip = socket.gethostbyname(server)
        print(f"  ✓ DNS резолвится: {server} → {ip}")
    except socket.gaierror as e:
        print(f"  ✗ Ошибка DNS: {e}")
        print("  → Проверьте интернет-соединение")
        return False
    
    # Шаг 2: TCP-соединение
    print("\n[2/7] Проверка TCP-соединения...")
    try:
        sock = socket.create_connection((server, port), timeout=10)
        sock.close()
        print(f"  ✓ TCP-порт {port} открыт")
    except socket.timeout:
        print(f"  ✗ Таймаут соединения с {server}:{port}")
        print("  → Проверьте firewall, антивирус")
        return False
    except ConnectionRefusedError:
        print(f"  ✗ Соединение отклонено")
        print(f"  → Сервер не принимает подключения на порту {port}")
        return False
    except Exception as e:
        print(f"  ✗ Ошибка TCP: {e}")
        return False
    
    # Шаг 3: SSL/TLS
    print("\n[3/7] Проверка SSL/TLS...")
    try:
        context = ssl.create_default_context()
        sock = socket.create_connection((server, port), timeout=10)
        ssl_sock = context.wrap_socket(sock, server_hostname=server)
        print(f"  ✓ SSL установлен")
        print(f"    Версия: {ssl_sock.version()}")
        print(f"    Шифр: {ssl_sock.cipher()[0]}")
        ssl_sock.close()
    except ssl.SSLError as e:
        print(f"  ✗ Ошибка SSL: {e}")
        print("  → Проблема с сертификатами")
        return False
    except Exception as e:
        print(f"  ✗ Ошибка SSL: {e}")
        return False
    
    # Шаг 4: IMAP-протокол
    print("\n[4/7] Проверка IMAP-протокола...")
    try:
        mail = imaplib.IMAP4_SSL(server, port, timeout=10)
        print(f"  ✓ IMAP-сервер ответил")
        welcome = mail.welcome.decode() if mail.welcome else 'нет'
        print(f"    Приветствие: {welcome}")
    except imaplib.IMAP4.error as e:
        print(f"  ✗ Ошибка IMAP: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Ошибка подключения: {e}")
        return False
    
    # Шаг 5: Аутентификация
    print("\n[5/7] Проверка аутентификации...")
    try:
        mail.login(login, password)
        print(f"  ✓ Аутентификация успешна")
    except imaplib.IMAP4.error as e:
        error_msg = str(e)
        print(f"  ✗ Ошибка аутентификации: {error_msg}")
        
        if "LOGIN disabled" in error_msg:
            print("  → Яндекс отключил обычный пароль")
            print("  → Создайте пароль приложения: https://id.yandex.ru/security")
        elif "Invalid credentials" in error_msg or "authentication failed" in error_msg.lower():
            print("  → Неверный логин или пароль")
            print("  → Если включена 2FA, используйте пароль приложения")
        elif "Account blocked" in error_msg:
            print("  → Аккаунт заблокирован")
            print("  → Проверьте почту через веб-интерфейс")
        
        try:
            mail.logout()
        except:
            pass
        return False
    except Exception as e:
        print(f"  ✗ Неожиданная ошибка: {e}")
        try:
            mail.logout()
        except:
            pass
        return False
    
    # Шаг 6: Выбор папки
    print("\n[6/7] Проверка папок...")
    try:
        status, folders = mail.list()
        if status == 'OK':
            folder_count = len(folders)
            print(f"  ✓ Найдено папок: {folder_count}")
            
            # Показываем первые 5 папок
            for folder in folders[:5]:
                folder_name = folder.decode().split('"/"')[-1].strip().strip('"')
                print(f"    - {folder_name}")
            if folder_count > 5:
                print(f"    ... и ещё {folder_count - 5}")
        
        # Выбираем INBOX
        status, data = mail.select('INBOX')
        if status == 'OK':
            message_count = int(data[0])
            print(f"  ✓ Папка INBOX: {message_count} писем")
        else:
            print(f"  ✗ Не удалось выбрать INBOX: {data}")
            mail.logout()
            return False
            
    except Exception as e:
        print(f"  ✗ Ошибка: {e}")
        try:
            mail.logout()
        except:
            pass
        return False
    
    # Шаг 7: Получение писем
    print("\n[7/7] Получение последних писем...")
    try:
        status, messages = mail.search(None, 'ALL')
        if status == 'OK':
            message_ids = messages[0].split()
            total = len(message_ids)
            print(f"  ✓ Всего писем: {total}")
            
            if total > 0:
                # Берём последние 3 письма
                recent_ids = message_ids[-3:]
                print(f"  ✓ Последние 3 письма:")
                
                for msg_id in recent_ids:
                    status, data = mail.fetch(msg_id, '(BODY[HEADER.FIELDS (SUBJECT FROM DATE)])')
                    if status == 'OK':
                        header = data[0][1].decode('utf-8', errors='ignore')
                        lines = header.strip().split('\n')
                        
                        subject = next((l.replace('Subject: ', '') for l in lines if l.startswith('Subject:')), '(без темы)')
                        from_addr = next((l.replace('From: ', '') for l in lines if l.startswith('From:')), '(неизвестно)')
                        date = next((l.replace('Date: ', '') for l in lines if l.startswith('Date:')), '(нет даты)')
                        
                        print(f"    [{msg_id.decode()}] {subject[:50]}")
                        print(f"         От: {from_addr[:50]}")
                        print(f"         Дата: {date}")
            else:
                print(f"  ⚠ Папка INBOX пуста")
        
        mail.logout()
        print("\n" + "=" * 70)
        print("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ УСПЕШНО!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"  ✗ Ошибка: {e}")
        try:
            mail.logout()
        except:
            pass
        return False


def main():
    """Главная функция."""
    import os
    from pathlib import Path
    from dotenv import load_dotenv
    
    # Ищем .env файл
    env_path = Path('.env')
    
    if env_path.exists():
        print(f"✓ Найден файл .env: {env_path.absolute()}")
        load_dotenv(env_path)
        print(f"✓ Настройки загружены из .env")
    else:
        print(f"⚠ Файл .env не найден в {Path.cwd()}")
        print(f"  Будут использоваться значения по умолчанию")
    
    # Читаем настройки
    server = os.getenv('IMAP_SERVER', 'imap.yandex.ru')
    login = os.getenv('IMAP_LOGIN')
    password = os.getenv('IMAP_PASSWORD')
    port = int(os.getenv('IMAP_PORT', '993'))
    
    # Показываем источник каждой настройки
    print(f"\nИспользуемые настройки:")
    print(f"  IMAP_SERVER  = {server} {'(из .env)' if os.getenv('IMAP_SERVER') else '(по умолчанию)'}")
    print(f"  IMAP_PORT    = {port} {'(из .env)' if os.getenv('IMAP_PORT') else '(по умолчанию)'}")
    
    if not login or not password:
        print(f"\n✗ Ошибка: IMAP_LOGIN или IMAP_PASSWORD не указаны!")
        print(f"\nДобавьте в файл .env:")
        print(f"  IMAP_LOGIN=your_email@yandex.ru")
        print(f"  IMAP_PASSWORD=your_password")
        return
    
    print(f"  IMAP_LOGIN   = {login} (из .env)")
    
    # Маскируем пароль
    if len(password) > 6:
        masked_password = password[:3] + '*' * (len(password) - 6) + password[-3:]
    else:
        masked_password = '***'
    print(f"  IMAP_PASSWORD = {masked_password} (из .env)")
    
    print()
    confirm = input("Начать диагностику? (y/n): ").strip().lower()
    if confirm != 'y':
        print("Отменено")
        return
    
    print()
    success = test_imap_connection(server, login, password, port)
    
    if not success:
        print("\n" + "=" * 70)
        print("❌ ДИАГНОСТИКА ЗАВЕРШЕНА С ОШИБКАМИ")
        print("=" * 70)
        print("\nРекомендации:")
        print("1. Проверьте настройки Яндекса: https://mail.yandex.ru → Настройки → Почтовые программы")
        print("2. Если включена 2FA, создайте пароль приложения: https://id.yandex.ru/security")
        print("3. Убедитесь, что используете правильный пароль в .env")
        print("4. Проверьте firewall и антивирус")


if __name__ == "__main__":
    main()