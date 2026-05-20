import socket
import os
import time
from datetime import datetime
import threading
import subprocess
import ctypes
import sys

# ================= CONFIG =================

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(BASE_PATH, "serv.conf")


def show_error(message):
    ctypes.windll.user32.MessageBoxW(
        0,
        message,
        "Настройка программы",
        0x10
    )


def load_config():

    required_fields = [
        "PORT",
        "REPORT_UPDATE_INTERVAL",
        "ACTIVITY_INTERVAL"
    ]

    # ===== CREATE CONFIG =====

    if not os.path.exists(CONFIG_FILE):

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write("PORT=\n")
            f.write("\n")
            f.write("REPORT_UPDATE_INTERVAL=\n")
            f.write("ACTIVITY_INTERVAL=\n")

        show_error(
            "Файл serv.conf был создан.\n\n"
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

        show_error(f"Ошибка чтения serv.conf\n\n{e}")

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
            "Заполните поля в serv.conf:\n\n"
            f"{fields}"
        )

        sys.exit(1)

    return config


config = load_config()

HOST = "0.0.0.0"

PORT = int(config["PORT"])

REPORT_UPDATE_INTERVAL = int(
    config["REPORT_UPDATE_INTERVAL"]
)

ACTIVITY_INTERVAL = int(
    config["ACTIVITY_INTERVAL"]
)

# ================= PATHS =================

BASE_DIR = "monitoring"

FULL_REPORTS_DIR = os.path.join(
    BASE_DIR,
    "full_reports"
)

os.makedirs(BASE_DIR, exist_ok=True)

os.makedirs(FULL_REPORTS_DIR, exist_ok=True)


# ================= FIREWALL =================

def add_to_firewall():

    if sys.platform == "win32":

        try:

            if ctypes.windll.shell32.IsUserAnAdmin():

                rule_name = "WorkTime_Server_Port"

                cmd = (
                    f'netsh advfirewall firewall add rule '
                    f'name="{rule_name}" '
                    f'dir=in action=allow '
                    f'protocol=TCP localport={PORT}'
                )

                subprocess.run(
                    f'netsh advfirewall firewall delete rule name="{rule_name}"',
                    shell=True,
                    capture_output=True
                )

                subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True
                )

        except Exception:
            pass


# ================= REPORTS =================

def generate_hourly_report():

    while True:

        try:

            now = datetime.now()

            date_str = now.strftime("%Y-%m-%d")

            report_filepath = os.path.join(
                FULL_REPORTS_DIR,
                f"{date_str}.txt"
            )

            try:

                pc_folders = [

                    d for d in os.listdir(BASE_DIR)

                    if os.path.isdir(
                        os.path.join(BASE_DIR, d)
                    )

                    and d != "full_reports"
                ]

            except FileNotFoundError:

                pc_folders = []

            report_lines = []

            report_lines.append(
                f"--- Сводный отчет за {date_str} "
                f"(Сформирован в "
                f"{now.strftime('%H:%M:%S')}) ---"
            )

            for pc in pc_folders:

                log_file = os.path.join(
                    BASE_DIR,
                    pc,
                    date_str,
                    "отчёт.txt"
                )

                if os.path.exists(log_file):

                    active_count = 0

                    with open(
                        log_file,
                        "r",
                        encoding="utf-8"
                    ) as f:

                        for line in f:

                            if "Сделан скриншот" in line:
                                active_count += 1

                    total_seconds = (
                        active_count *
                        ACTIVITY_INTERVAL
                    )

                    hours = total_seconds // 3600

                    minutes = (
                        total_seconds % 3600
                    ) // 60

                    seconds = total_seconds % 60

                    time_str = (
                        f"{hours:02d}:"
                        f"{minutes:02d}:"
                        f"{seconds:02d}"
                    )

                    report_lines.append(
                        f"{pc} - {time_str} Суммарно время активности"
                    )

                else:

                    report_lines.append(
                        f"{pc} - не запускался"
                    )

            with open(
                report_filepath,
                "w",
                encoding="utf-8"
            ) as f:

                f.write(
                    "\n".join(report_lines) + "\n"
                )

        except Exception:
            pass

        time.sleep(REPORT_UPDATE_INTERVAL)


# ================= NETWORK =================

def recv_all(conn):

    raw_len = conn.recv(4)

    if not raw_len:
        return None

    length = int.from_bytes(raw_len, 'big')

    if length > 50 * 1024 * 1024:
        return None

    data = b''

    while len(data) < length:

        chunk = conn.recv(
            min(4096, length - len(data))
        )

        if not chunk:
            break

        data += chunk

    if len(data) != length:
        return None

    return data


# ================= SAVE LOG =================

def save_log(pc_name, date_str, log_line):

    path = os.path.join(
        BASE_DIR,
        pc_name,
        date_str
    )

    os.makedirs(path, exist_ok=True)

    log_file = os.path.join(
        path,
        "отчёт.txt"
    )

    with open(
        log_file,
        "a",
        encoding="utf-8"
    ) as f:

        f.write(log_line + "\n")


# ================= SAVE SCREENSHOT =================

def save_screenshot(
    pc_name,
    date_str,
    filename,
    img_bytes
):

    path = os.path.join(
        BASE_DIR,
        pc_name,
        date_str,
        "screenshots"
    )

    os.makedirs(path, exist_ok=True)

    filepath = os.path.join(path, filename)

    with open(filepath, "wb") as f:
        f.write(img_bytes)


# ================= CLIENT =================

def handle_client(conn, addr):

    try:

        while True:

            cmd = conn.recv(4).decode()

            if not cmd:
                break

            if cmd == "LOG":

                data = recv_all(conn)

                if data:

                    text_data = data.decode('utf-8')

                    parts = text_data.split('\n', 2)

                    if len(parts) >= 3:

                        pc_name, date_str, log_line = parts

                        save_log(
                            pc_name,
                            date_str,
                            log_line
                        )

                        conn.send(b"OK")

            elif cmd == "SCRN":

                data = recv_all(conn)

                if data:

                    newline_count = 0

                    header_end_pos = 0

                    for i, byte in enumerate(data):

                        if byte == ord('\n'):

                            newline_count += 1

                            if newline_count == 3:

                                header_end_pos = i

                                break

                    if header_end_pos > 0:

                        header = data[
                            :header_end_pos
                        ].decode('utf-8')

                        img_data = data[
                            header_end_pos + 1:
                        ]

                        parts = header.split('\n')

                        if len(parts) >= 3:

                            pc_name = parts[0]

                            date_str = parts[1]

                            filename = parts[2]

                            save_screenshot(
                                pc_name,
                                date_str,
                                filename,
                                img_data
                            )

                            conn.send(b"OK")

    except Exception:
        pass

    finally:
        conn.close()


# ================= SERVER =================

def start_server():

    add_to_firewall()

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, PORT))

    server.listen(5)

    report_thread = threading.Thread(
        target=generate_hourly_report
    )

    report_thread.daemon = True

    report_thread.start()

    while True:

        try:

            conn, addr = server.accept()

            thread = threading.Thread(
                target=handle_client,
                args=(conn, addr)
            )

            thread.daemon = True

            thread.start()

        except Exception:
            pass


# ================= START =================

if __name__ == "__main__":

    try:

        start_server()

    except KeyboardInterrupt:
        pass
