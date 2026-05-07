import socket
import os
from datetime import datetime
import threading

HOST = '0.0.0.0'      # слушаем все интерфейсы
PORT = 12345
BASE_DIR = "monitoring"   # корневая папка для всех отчётов
os.makedirs(BASE_DIR, exist_ok=True)

def handle_client(conn, addr):
    print(f"[+] Подключён {addr}")
    try:
        while True:
            # Сначала читаем команду (4 байта)
            cmd = conn.recv(4).decode()
            if not cmd:
                break
                
            if cmd == "LOG":
                # Приём лога (текстовые данные)
                data = recv_all(conn)
                if data:
                    # Декодируем как текст
                    text_data = data.decode('utf-8')
                    parts = text_data.split('\n', 2)
                    if len(parts) >= 3:
                        pc_name, date_str, log_line = parts
                        save_log(pc_name, date_str, log_line)
                        conn.send(b"OK")
                    else:
                        conn.send(b"ERR")
                        
            elif cmd == "SCRN":
                # Приём скриншота (бинарные данные)
                data = recv_all(conn)
                if data:
                    # Находим позицию третьего перевода строки
                    # Формат: имя_компа\nдата\nимя_файла\n[бинарные данные]
                    newline_count = 0
                    header_end_pos = 0
                    
                    for i, byte in enumerate(data):
                        if byte == ord('\n'):
                            newline_count += 1
                            if newline_count == 3:
                                header_end_pos = i
                                break
                    
                    if header_end_pos > 0:
                        # Заголовок (3 строки)
                        header = data[:header_end_pos].decode('utf-8')
                        # Бинарные данные изображения (остальная часть)
                        img_data = data[header_end_pos + 1:]
                        
                        parts = header.split('\n')
                        if len(parts) >= 3:
                            pc_name, date_str, filename = parts[0], parts[1], parts[2]
                            save_screenshot(pc_name, date_str, filename, img_data)
                            conn.send(b"OK")
                        else:
                            conn.send(b"ERR")
                    else:
                        conn.send(b"ERR")
            else:
                break
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def recv_all(conn):
    """Получение данных известной длины"""
    # Сначала читаем длину (4 байта)
    raw_len = conn.recv(4)
    if not raw_len:
        return None
    length = int.from_bytes(raw_len, 'big')
    
    # Защита от слишком больших файлов
    if length > 50 * 1024 * 1024:  # 50 MB максимум
        print(f"  [Ошибка] Файл слишком большой: {length} байт")
        return None
    
    data = b''
    while len(data) < length:
        chunk = conn.recv(min(4096, length - len(data)))
        if not chunk:
            break
        data += chunk
    
    if len(data) != length:
        print(f"  [Ошибка] Получено {len(data)} из {length} байт")
        return None
    
    return data

def save_log(pc_name, date_str, log_line):
    path = os.path.join(BASE_DIR, pc_name, date_str)
    os.makedirs(path, exist_ok=True)
    log_file = os.path.join(path, "отчёт.txt")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")
    print(f"  [Сохранён лог] {pc_name}/{date_str}/отчёт.txt: {log_line}")

def save_screenshot(pc_name, date_str, filename, img_bytes):
    path = os.path.join(BASE_DIR, pc_name, date_str, "screenshots")
    os.makedirs(path, exist_ok=True)
    filepath = os.path.join(path, filename)
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    print(f"  [Сохранён скриншот] {pc_name}/{date_str}/screenshots/{filename} (размер: {len(img_bytes)} байт)")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # Позволяет перезапускать сервер без ожидания
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[*] СЕРВЕР ЗАПУЩЕН на порту {PORT}")
    print(f"[*] IP адрес этого компьютера:")
    
    # Показываем все IP адреса этого компьютера
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"    - Локальный: {local_ip}")
    
    # Получаем все IP адреса в сети
    try:
        import netifaces
    except ImportError:
        print(f"    - Для просмотра всех IP установите: pip install netifaces")
    
    print(f"[*] Папка для сохранения: {os.path.abspath(BASE_DIR)}")
    print(f"[*] Ожидание подключений...")
    print("-" * 60)
    
    while True:
        try:
            conn, addr = server.accept()
            print(f"[+] Новое подключение от {addr}")
            thread = threading.Thread(target=handle_client, args=(conn, addr))
            thread.daemon = True
            thread.start()
            print(f"    [*] Активных подключений: {threading.active_count() - 1}")
        except KeyboardInterrupt:
            print("\n[*] Сервер остановлен")
            break
        except Exception as e:
            print(f"[!] Ошибка: {e}")

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[*] Сервер завершил работу")
