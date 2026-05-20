import time
import os
import socket
from datetime import datetime
from pynput import mouse, keyboard
import pyautogui
import ctypes
import sys
from io import BytesIO

# ================= CONFIG =================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_DIR, "user.conf")


def show_error(message):
    ctypes.windll.user32.MessageBoxW(
        0,
        message,
        "Настройка программы",
        0x10
    )


def load_config():

    required_fields = [
        "SERVER_HOST",
        "SERVER_PORT",
        "SCREENSHOT_INTERVAL",
        "IDLE_THRESHOLD"
    ]

    # ===== CREATE CONFIG =====

    if not os.path.exists(CONFIG_FILE):

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("SERVER_HOST=\n")
            f.write("SERVER_PORT=\n")
            f.write("\n")
            f.write("SCREENSHOT_INTERVAL=\n")
            f.write("IDLE_THRESHOLD=\n")

        show_error(
            "Файл user.conf был создан.\n\n"
            "Заполните его вручную и перезапустите программу."
        )

        sys.exit(1)

    # ===== READ CONFIG =====

    config = {}

    try:

        with open(CONFIG_FILE, "r", encoding="utf-8") as f:

            for line in f:

                line = line.strip()

                if not line:
                    continue

                if line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)

                config[key.strip()] = value.strip()

    except Exception as e:

        show_error(f"Ошибка чтения user.conf\n\n{e}")

        sys.exit(1)

    # ===== VALIDATE =====

    missing = []

    for field in required_fields:

        if field not in config:
            missing.append(field)

        elif config[field] == "":
            missing.append(field)

    if missing:

        fields = "\n".join(missing)

        show_error(
            "Заполните поля в user.conf:\n\n"
            f"{fields}"
        )

        sys.exit(1)

    return config


config = load_config()

SERVER_HOST = config["SERVER_HOST"]

SERVER_PORT = int(config["SERVER_PORT"])

SCREENSHOT_INTERVAL = int(
    config["SCREENSHOT_INTERVAL"]
)

IDLE_THRESHOLD = int(
    config["IDLE_THRESHOLD"]
)

COMPUTER_NAME = socket.gethostname()

# ================= ACTIVITY =================

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


mouse_listener = mouse.Listener(
    on_move=on_move,
    on_click=on_click
)

keyboard_listener = keyboard.Listener(
    on_press=on_press
)

mouse_listener.start()

keyboard_listener.start()

# ================= SEND LOG =================


def send_log(message):

    date_str = datetime.now().strftime("%Y-%m-%d")

    timestamp = datetime.now().strftime("%H:%M:%S")

    log_line = f"{timestamp} - {message}"

    data = (
        f"{COMPUTER_NAME}\n"
        f"{date_str}\n"
        f"{log_line}"
    ).encode()

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        sock.connect((SERVER_HOST, SERVER_PORT))

        sock.send(b"LOG")

        sock.send(
            len(data).to_bytes(4, 'big')
        )

        sock.send(data)

        sock.recv(2)

        sock.close()

    except Exception:
        pass


# ================= SEND SCREENSHOT =================


def send_screenshot(image):

    date_str = datetime.now().strftime("%Y-%m-%d")

    filename = datetime.now().strftime(
        "%Y-%m-%d_%H-%M-%S.png"
    )

    buffer = BytesIO()

    image.save(buffer, format="PNG")

    img_bytes = buffer.getvalue()

    header = (
        f"{COMPUTER_NAME}\n"
        f"{date_str}\n"
        f"{filename}\n"
    ).encode()

    data = header + img_bytes

    try:

        sock = socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        )

        sock.connect((SERVER_HOST, SERVER_PORT))

        sock.send(b"SCRN")

        sock.send(
            len(data).to_bytes(4, 'big')
        )

        sock.send(data)

        sock.recv(2)

        sock.close()

    except Exception:
        pass


# ================= MAIN LOOP =================

while True:

    current_time = time.time()

    idle_time = (
        current_time - last_activity_time
    )

    if idle_time < IDLE_THRESHOLD:

        screenshot = pyautogui.screenshot()

        send_log("Сделан скриншот")

        send_screenshot(screenshot)

    else:

        send_log("Пользователь неактивен")

    time.sleep(SCREENSHOT_INTERVAL)