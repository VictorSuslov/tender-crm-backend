import imaplib
import socket
import ssl
from typing import Dict, Any, Optional
from app.config import settings


class IMAPChecker:
    """Сервис для диагностики IMAP-подключения."""
    
    @staticmethod
    async def check_connection() -> Dict[str, Any]:
        """
        Полная диагностика IMAP-подключения.
        
        Returns:
            {
                "success": bool,
                "server": str,
                "login": str,
                "steps": [
                    {"name": str, "status": "ok"|"error", "message": str, "details": str}
                ],
                "summary": str,
                "inbox_count": int
            }
        """
        result = {
            "success": False,
            "server": settings.IMAP_SERVER,
            "login": settings.IMAP_LOGIN,
            "steps": [],
            "summary": "",
            "inbox_count": 0,
        }
        
        server = settings.IMAP_SERVER
        login = settings.IMAP_LOGIN
        password = settings.IMAP_PASSWORD
        port = 993
        
        # Шаг 1: DNS
        try:
            ip = socket.gethostbyname(server)
            result["steps"].append({
                "name": "DNS",
                "status": "ok",
                "message": f"{server} → {ip}",
                "details": "DNS резолвится корректно"
            })
        except socket.gaierror as e:
            result["steps"].append({
                "name": "DNS",
                "status": "error",
                "message": str(e),
                "details": "Проверьте интернет-соединение"
            })
            result["summary"] = "Ошибка DNS: сервер не найден"
            return result
        
        # Шаг 2: TCP
        try:
            sock = socket.create_connection((server, port), timeout=10)
            sock.close()
            result["steps"].append({
                "name": "TCP",
                "status": "ok",
                "message": f"Порт {port} открыт",
                "details": "TCP-соединение установлено"
            })
        except socket.timeout:
            result["steps"].append({
                "name": "TCP",
                "status": "error",
                "message": "Таймаут соединения",
                "details": "Проверьте firewall и антивирус"
            })
            result["summary"] = "TCP-соединение не установлено"
            return result
        except Exception as e:
            result["steps"].append({
                "name": "TCP",
                "status": "error",
                "message": str(e),
                "details": "Ошибка TCP-соединения"
            })
            result["summary"] = "TCP-соединение не установлено"
            return result
        
        # Шаг 3: SSL
        try:
            context = ssl.create_default_context()
            sock = socket.create_connection((server, port), timeout=10)
            ssl_sock = context.wrap_socket(sock, server_hostname=server)
            version = ssl_sock.version()
            cipher = ssl_sock.cipher()[0]
            ssl_sock.close()
            result["steps"].append({
                "name": "SSL",
                "status": "ok",
                "message": f"{version}",
                "details": f"Шифр: {cipher}"
            })
        except Exception as e:
            result["steps"].append({
                "name": "SSL",
                "status": "error",
                "message": str(e),
                "details": "Проблема с SSL-сертификатами"
            })
            result["summary"] = "Ошибка SSL"
            return result
        
        # Шаг 4: IMAP + аутентификация
        mail = None
        try:
            mail = imaplib.IMAP4_SSL(server, port, timeout=10)
            mail.login(login, password)
            result["steps"].append({
                "name": "Аутентификация",
                "status": "ok",
                "message": "Успешно",
                "details": f"Логин: {login}"
            })
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            
            if "LOGIN disabled" in error_msg:
                details = "Яндекс отключил обычный пароль. Создайте пароль приложения: https://id.yandex.ru/security"
            elif "Invalid credentials" in error_msg or "authentication failed" in error_msg.lower():
                details = "Неверный логин или пароль. Если включена 2FA, используйте пароль приложения"
            elif "Account blocked" in error_msg:
                details = "Аккаунт заблокирован. Проверьте почту через веб-интерфейс"
            else:
                details = error_msg
            
            result["steps"].append({
                "name": "Аутентификация",
                "status": "error",
                "message": error_msg,
                "details": details
            })
            result["summary"] = "Ошибка аутентификации"
            try:
                mail.logout()
            except:
                pass
            return result
        except Exception as e:
            result["steps"].append({
                "name": "Аутентификация",
                "status": "error",
                "message": str(e),
                "details": "Неожиданная ошибка"
            })
            result["summary"] = "Ошибка подключения"
            try:
                mail.logout()
            except:
                pass
            return result
        
        # Шаг 5: Папки
        try:
            status, folders = mail.list()
            if status == 'OK':
                result["steps"].append({
                    "name": "Папки",
                    "status": "ok",
                    "message": f"Найдено {len(folders)} папок",
                    "details": "INBOX, Отправленные, Черновики и др."
                })
            else:
                result["steps"].append({
                    "name": "Папки",
                    "status": "error",
                    "message": "Не удалось получить список папок",
                    "details": str(folders)
                })
        except Exception as e:
            result["steps"].append({
                "name": "Папки",
                "status": "error",
                "message": str(e),
                "details": "Ошибка получения списка папок"
            })
        
        # Шаг 6: INBOX
        try:
            status, data = mail.select('INBOX')
            if status == 'OK':
                inbox_count = int(data[0])
                result["inbox_count"] = inbox_count
                result["steps"].append({
                    "name": "INBOX",
                    "status": "ok",
                    "message": f"{inbox_count} писем",
                    "details": "Папка доступна для чтения"
                })
            else:
                result["steps"].append({
                    "name": "INBOX",
                    "status": "error",
                    "message": "Не удалось открыть INBOX",
                    "details": str(data)
                })
        except Exception as e:
            result["steps"].append({
                "name": "INBOX",
                "status": "error",
                "message": str(e),
                "details": "Ошибка чтения INBOX"
            })
        
        # Завершение
        try:
            mail.logout()
        except:
            pass
        
        # Итоговый статус
        all_ok = all(step["status"] == "ok" for step in result["steps"])
        result["success"] = all_ok
        
        if all_ok:
            result["summary"] = f"✓ Подключение работает. В ящике {result['inbox_count']} писем."
        else:
            failed_steps = [s["name"] for s in result["steps"] if s["status"] == "error"]
            result["summary"] = f"✗ Ошибки в этапах: {', '.join(failed_steps)}"
        
        return result