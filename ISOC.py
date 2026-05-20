import platform
import re
import socket
import os
import subprocess
import shutil
from datetime import datetime
import sys
import json
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import html  # для экранирования

# ---------------------------------------------------------
# НАСТРОЙКИ
# ---------------------------------------------------------
SENDER_EMAIL = "scriptmail_noreply@mail.ru"
SENDER_PASSWORD = "d3IczDezeY7dkGSgtbq5"
RECIPIENT_EMAIL = "vanja05102007@gmail.com"

LIMIT_FILE = os.path.join(os.environ.get('TEMP', '.'), ".sys_run_cache.json")
MAX_RUNS_PER_HOUR = 7

# ---------------------------------------------------------
# СБОР ДАННЫХ (ПОЛНЫЙ JSON)
# ---------------------------------------------------------
def run_hw(cmd, shell=False, encoding=None):
    """Запуск команды и возврат stdout"""
    try:
        out = subprocess.check_output(
            cmd,
            shell=shell,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=encoding or "cp866",
            errors="ignore"
        )
        return out.strip()
    except Exception:
        return ""

def run(cmd, shell=False, encoding=None):
    """Выполнить команду и вернуть stdout"""
    try:
        out = subprocess.check_output(
            cmd,
            shell=shell,
            stderr=subprocess.STDOUT,
            text=True,
            encoding=encoding or "cp866",
            errors="ignore"
        )
        return out.strip()
    except Exception:
        return ""

def gather_network_info():
    res = {}
    res["collected_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
    res["hostname"] = socket.gethostname()
    res["network"] = get_network_info()
    return res

def get_all_users():
    """Получить всех локальных пользователей Windows"""
    users = []
    out = run("wmic useraccount get name /format:list", shell=True)
    if out:
        for line in out.splitlines():
            if line.startswith("Name="):
                name = line.split("=", 1)[1].strip()
                if name:
                    users.append(name)
    return users

def get_last_logon_users():
    """Последний вход пользователей через `net user`"""
    logons = {}
    if platform.system() == "Windows":
        users = get_all_users()
        for user in users:
            out = run(f'net user "{user}"', shell=True, encoding="cp866")
            last_logon = "N/A"
            if out:
                for line in out.splitlines():
                    if "Последний вход" in line:
                        parts = line.split("Последний вход")
                        if len(parts) > 1:
                            last_logon = parts[1].strip()
                        break
            logons[user] = last_logon
    return logons

def gather_system_info():
    res = {}
    res["collected_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
    res["hostname"] = socket.gethostname()

    res["os"] = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "pretty": platform.platform(),
    }

    return res

def get_cpu_info():
    model = platform.processor() or "Неизвестно"
    cores = None
    threads = None
    serial = "N/A"

    if platform.system() == "Windows":
        # Получаем полное имя из wmic
        out = run_hw("wmic cpu get Name /value", shell=True)
        if out:
            for line in out.splitlines():
                if "Name=" in line:
                    full_name = line.split("=", 1)[1].strip()
                    if full_name and full_name != "N/A":
                        model = full_name

        # Серийный номер (ProcessorId)
        out = run_hw("wmic cpu get ProcessorId /value", shell=True)
        if out:
            for line in out.splitlines():
                if "ProcessorId" in line:
                    serial = line.split("=")[1].strip()

        # Количество физических ядер
        out = run_hw("wmic cpu get NumberOfCores /value", shell=True)
        if out:
            for line in out.splitlines():
                if "NumberOfCores=" in line:
                    try:
                        cores = int(line.split("=")[1].strip())
                    except:
                        pass

        # Количество логических процессоров (потоков)
        out = run_hw("wmic cpu get NumberOfLogicalProcessors /value", shell=True)
        if out:
            for line in out.splitlines():
                if "NumberOfLogicalProcessors=" in line:
                    try:
                        threads = int(line.split("=")[1].strip())
                    except:
                        pass

        # Частоты
        out = run_hw("wmic cpu get CurrentClockSpeed /value", shell=True)
        current_speed = "N/A"
        if out:
            for line in out.splitlines():
                if "CurrentClockSpeed=" in line:
                    speed_mhz = line.split("=")[1].strip()
                    if speed_mhz and speed_mhz.isdigit():
                        current_speed = f"{int(speed_mhz) / 1000:.2f} GHz"

        out = run_hw("wmic cpu get MaxClockSpeed /value", shell=True)
        max_speed = "N/A"
        if out:
            for line in out.splitlines():
                if "MaxClockSpeed=" in line:
                    speed_mhz = line.split("=")[1].strip()
                    if speed_mhz and speed_mhz.isdigit():
                        max_speed = f"{int(speed_mhz) / 1000:.2f} GHz"

        if "@" not in model and max_speed != "N/A":
            model = f"{model} @ {max_speed}"

    if cores is None:
        if threads is not None:
            cores = None
        else:
            logical = os.cpu_count()
            if logical is not None:
                threads = logical
                cores = None
    if threads is None:
        threads = os.cpu_count()
    if cores is None:
        cores = threads if threads is not None else "N/A"

    return {
        "model": model,
        "cores": cores,
        "threads": threads if threads is not None else "N/A",
        "serial": serial,
        "max_speed": max_speed if 'max_speed' in locals() else "N/A"
    }

def clean_gpu_serial(pnp_id: str) -> str:
    if not pnp_id or pnp_id == "N/A":
        return "N/A"
    parts = pnp_id.split("\\")
    if parts:
        last = parts[-1]
        cleaned = "".join(ch for ch in last if ch.isalnum() or ch == '-')
        return cleaned if cleaned else "N/A"
    return "N/A"

def get_gpu_names():
    names = []
    if platform.system() == "Windows":
        out = run_hw("wmic path win32_videocontroller get Name /value", shell=True)
        if out:
            for line in out.splitlines():
                if "Name=" in line:
                    name = line.split("=", 1)[1].strip()
                    if name and name != "N/A":
                        names.append(name)
                    else:
                        names.append("Неизвестно")
    return names

def get_gpu_memory():
    memories = []
    if platform.system() == "Windows":
        out = run_hw("wmic path win32_videocontroller get AdapterRAM /value", shell=True)
        if out:
            for line in out.splitlines():
                if "AdapterRAM=" in line:
                    memory_str = line.split("=", 1)[1].strip()
                    if memory_str and memory_str != "N/A":
                        try:
                            memory_bytes = int(memory_str)
                            memory_gb = round(memory_bytes / (1024**3), 2)
                            memories.append(memory_gb)
                        except:
                            memories.append("N/A")
                    else:
                        memories.append("N/A")
    return memories

def get_gpu_drivers():
    drivers = []
    if platform.system() == "Windows":
        out = run_hw("wmic path win32_videocontroller get DriverVersion /value", shell=True)
        if out:
            for line in out.splitlines():
                if "DriverVersion=" in line:
                    driver = line.split("=", 1)[1].strip()
                    if driver and driver != "N/A":
                        drivers.append(driver)
                    else:
                        drivers.append("N/A")
    return drivers

def get_gpu_serials():
    serials = []
    if platform.system() == "Windows":
        out = run_hw("wmic path win32_videocontroller get PNPDeviceID /value", shell=True)
        if out:
            for line in out.splitlines():
                if "PNPDeviceID=" in line:
                    serial = line.split("=", 1)[1].strip()
                    if serial and serial != "N/A":
                        cleaned_serial = clean_gpu_serial(serial)
                        serials.append(cleaned_serial)
                    else:
                        serials.append("N/A")
    return serials

def get_gpu_info():
    gpus = []
    names = get_gpu_names()
    memories = get_gpu_memory()
    drivers = get_gpu_drivers()
    serials = get_gpu_serials()
    max_gpus = max(len(names), len(memories), len(drivers), len(serials))
    for i in range(max_gpus):
        gpu = {}
        gpu["name"] = names[i] if i < len(names) else "Неизвестно"
        gpu["memory_gb"] = memories[i] if i < len(memories) else "N/A"
        gpu["driver_version"] = drivers[i] if i < len(drivers) else "N/A"
        gpu["serial"] = serials[i] if i < len(serials) else "N/A"
        gpus.append(gpu)
    return gpus

def get_motherboard_info():
    motherboard = {}
    if platform.system() == "Windows":
        out = run_hw("wmic baseboard get Product,Manufacturer,SerialNumber /format:list", shell=True)
        if out:
            for line in out.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    if k.strip() == "Product":
                        motherboard["model"] = v.strip()
                    elif k.strip() == "Manufacturer":
                        motherboard["manufacturer"] = v.strip()
                    elif k.strip() == "SerialNumber":
                        motherboard["serial"] = v.strip()

        if not motherboard.get("model"):
            out = run_hw("wmic computersystem get Model /format:list", shell=True)
            if out:
                for line in out.splitlines():
                    if "Model=" in line:
                        motherboard["model"] = line.split("=")[1].strip()
    # количество слотов памяти (примерное)
    motherboard["memory_slots"] = "N/A"
    return motherboard

def get_ram_info():
    ram = {"total": 0, "modules": []}
    if platform.system() != "Windows":
        return ram

    capacity_out = run_hw("wmic memorychip get Capacity /format:list", shell=True)
    serial_out = run_hw("wmic memorychip get SerialNumber /format:list", shell=True)
    manufacturer_out = run_hw("wmic memorychip get Manufacturer /format:list", shell=True)

    if (not capacity_out or "No Instance(s) Available" in capacity_out or
        not serial_out or "No Instance(s) Available" in serial_out or
        not manufacturer_out or "No Instance(s) Available" in manufacturer_out):
        return ram

    capacities = []
    lines = capacity_out.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("Capacity="):
            try:
                capacity_value = line.split("=", 1)[1]
                capacities.append(round(int(capacity_value) / 1024**3, 2))
            except:
                capacities.append(0)

    serials = []
    lines = serial_out.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("SerialNumber="):
            serial_value = line.split("=", 1)[1]
            if serial_value and serial_value != "None" and serial_value != "":
                serials.append(serial_value)
            else:
                serials.append("N/A")

    manufacturers = []
    lines = manufacturer_out.splitlines()
    for line in lines:
        line = line.strip()
        if line.startswith("Manufacturer="):
            manufacturer_value = line.split("=", 1)[1]
            if manufacturer_value and manufacturer_value != "None" and manufacturer_value != "":
                manufacturers.append(manufacturer_value)
            else:
                manufacturers.append("N/A")

    modules = []
    for i in range(max(len(capacities), len(serials), len(manufacturers))):
        module = {}
        if i < len(capacities):
            module["capacity"] = capacities[i]
        else:
            module["capacity"] = 0
        if i < len(serials):
            module["serial"] = serials[i]
        else:
            module["serial"] = "N/A"
        if i < len(manufacturers):
            module["manufacturer"] = manufacturers[i]
        else:
            module["manufacturer"] = "N/A"
        # part_number не собираем, оставим заглушку
        module["part_number"] = "N/A"
        modules.append(module)

    ram["modules"] = modules
    total_gb = sum(m.get("capacity", 0) for m in modules)
    ram["total"] = round(total_gb, 2)
    return ram

def get_bios_info():
    bios = {}
    if platform.system() == "Windows":
        out = run_hw("wmic bios get SerialNumber,SMBIOSBIOSVersion /format:list", shell=True)
        if out:
            for line in out.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    bios[k.strip()] = v.strip()
    return bios

def parse_disk_table(output):
    disks = []
    if not output or "No Instance(s) Available" in output:
        return disks
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if len(lines) < 2:
        return disks
    header = lines[0]
    data_lines = lines[1:]

    media_type_pos = header.find("MediaType")
    model_pos = header.find("Model")
    serial_pos = header.find("SerialNumber")
    size_pos = header.find("Size")

    if media_type_pos == -1:
        media_type_pos = header.find("Media Type")
    if model_pos == -1:
        model_pos = header.find("Model")
    if serial_pos == -1:
        serial_pos = header.find("Serial Number")
    if size_pos == -1:
        size_pos = header.find("Size")

    if media_type_pos == -1:
        media_type_pos = 0
    if model_pos == -1:
        model_pos = 20
    if serial_pos == -1:
        serial_pos = 60
    if size_pos == -1:
        size_pos = 100

    for line in data_lines:
        media_type = line[media_type_pos:model_pos].strip()
        model = line[model_pos:serial_pos].strip()
        serial = line[serial_pos:size_pos].strip()

        if size_pos < len(line):
            size_str = line[size_pos:].strip()
        else:
            size_str = "0"

        disk_info = {}
        disk_info["model"] = model if model else "N/A"
        manufacturer = "N/A"
        if model != "N/A":
            parts = model.split()
            if parts:
                manufacturer = parts[0]
        disk_info["manufacturer"] = manufacturer
        disk_info["serial"] = serial if serial else "N/A"

        try:
            size_gb = round(int(size_str) / (1024**3), 2)
        except:
            size_gb = 0
        disk_info["size_gb"] = size_gb

        media_type_lower = media_type.lower()
        model_lower = model.lower()
        if ("ssd" in media_type_lower or "solid" in media_type_lower or
            "ssd" in model_lower or "nvme" in model_lower):
            disk_info["disk_type"] = "SSD"
        elif ("hdd" in media_type_lower or "hard" in media_type_lower or
              "hdd" in model_lower or "wd" in model_lower or "seagate" in model_lower):
            disk_info["disk_type"] = "HDD"
        else:
            disk_info["disk_type"] = "N/A"
        disks.append(disk_info)
    return disks

def get_disk_info():
    if platform.system() != "Windows":
        return []
    commands = [
        "wmic diskdrive get Model,SerialNumber,Size,MediaType /format:table",
        "wmic diskdrive get MediaType,Model,SerialNumber,Size /format:table",
        "wmic diskdrive list brief /format:table"
    ]
    for cmd in commands:
        out = run_hw(cmd, shell=True)
        if out and "No Instance(s) Available" not in out:
            disks = parse_disk_table(out)
            if disks:
                return disks
    return []

def get_logical_disks():
    logical_disks = []
    if platform.system() == "Windows":
        for drive_letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_path = f"{drive_letter}:\\"
            if os.path.exists(drive_path):
                try:
                    total, used, free = shutil.disk_usage(drive_path)
                    total_gb = round(total / (1024**3), 2)
                    free_gb = round(free / (1024**3), 2)

                    fs_type = "N/A"
                    try:
                        fs_out = run_hw(f"fsutil fsinfo volumeinfo {drive_letter}:", shell=True)
                        if "File System Name" in fs_out:
                            for line in fs_out.splitlines():
                                if "File System Name" in line:
                                    fs_type = line.split(":")[1].strip()
                                    break
                    except:
                        pass

                    logical_disks.append({
                        "drive": drive_path,
                        "size_gb": total_gb,
                        "free_gb": free_gb,
                        "filesystem": fs_type
                    })
                except:
                    pass
    return logical_disks

def gather_hardware_info():
    res = {}
    res["collected_at"] = datetime.now().isoformat(sep=" ", timespec="seconds")
    res["cpu"] = get_cpu_info()
    res["gpu"] = get_gpu_info()
    res["motherboard"] = get_motherboard_info()
    res["ram"] = get_ram_info()
    res["bios"] = get_bios_info()
    res["physical_disks"] = get_disk_info()
    res["logical_disks"] = get_logical_disks()
    return res

def get_network_info():
    network_info = []
    if platform.system() == "Windows":
        out = run("ipconfig /all", shell=True)
        if out:
            sections = re.split(r'\n\s*\n', out)
            current_adapter = {}
            for section in sections:
                lines = [line.strip() for line in section.split("\n") if line.strip()]
                if not lines:
                    continue
                if ':' not in lines[0]:
                    if current_adapter:
                        network_info.append(current_adapter)
                    current_adapter = {
                        'description': lines[0],
                        'physical_address': 'N/A',
                        'ipv4': [],
                        'ipv6': [],
                        'dns_servers': [],
                        'gateway': 'N/A',
                        'dhcp_enabled': 'N/A'
                    }
                for line in lines:
                    if "Physical Address" in line or "Физический адрес" in line:
                        m = re.search(r":\s*([\w-]+)", line)
                        if m:
                            current_adapter['physical_address'] = m.group(1)
                    if "IPv4" in line:
                        m = re.search(r":\s*([\d\.]+)", line)
                        if m:
                            current_adapter['ipv4'].append(m.group(1))
                    if "IPv6" in line:
                        m = re.search(r":\s*([\w:]+)", line)
                        if m:
                            current_adapter['ipv6'].append(m.group(1))
                    if "Default Gateway" in line or "Основной шлюз" in line:
                        m = re.search(r":\s*([\d\.]+)", line)
                        if m:
                            current_adapter['gateway'] = m.group(1)
                    if "DNS" in line:
                        dns = re.findall(r"\d+\.\d+\.\d+\.\d+", section)
                        current_adapter["dns_servers"] = dns
            if current_adapter:
                network_info.append(current_adapter)
    # приведём ключи к виду, ожидаемому в HTML (mac_address)
    for adapter in network_info:
        adapter['mac_address'] = adapter.pop('physical_address', 'N/A')
    return network_info

def gather_all():
    sys_data = gather_system_info()
    hw_data = gather_hardware_info()
    return {
        "collected_at": sys_data["collected_at"],
        "hostname": sys_data["hostname"],
        "os": sys_data["os"],
        "users": get_last_logon_users(),
        "hardware": hw_data,
        "network": get_network_info()
    }

# ---------------------------------------------------------
# ФОРМИРОВАНИЕ HTML ОТЧЁТА НА ОСНОВЕ СОБРАННЫХ ДАННЫХ
# ---------------------------------------------------------
def generate_html_report(data):
    hostname = data['hostname']
    collected_at = data['collected_at']
    os_info = data['os']
    hardware = data['hardware']
    network = data['network']
    users = data['users']

    cpu = hardware['cpu']
    gpu_list = hardware['gpu']
    motherboard = hardware['motherboard']
    ram = hardware['ram']
    bios = hardware['bios']
    physical_disks = hardware['physical_disks']
    logical_disks = hardware['logical_disks']

    total_ram = ram.get('total', 0)
    ram_modules = ram.get('modules', [])
    memory_slots = len(ram_modules) if ram_modules else "N/A"
    motherboard['memory_slots'] = memory_slots

    # Стили (скопированы из visual.txt, адаптированы)
    styles = """
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f4f6f9;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            padding: 20px;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid lightblue;
            padding-bottom: 10px;
        }
        .computer-section {
            margin-bottom: 30px;
            padding: 20px;
            background: #f9f9f9;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .computer-section h3 {
            margin-top: 0;
            color: #2c3e50;
            border-bottom: 2px solid lightblue;
            padding-bottom: 10px;
        }
        .computer-section h4 {
            margin: 20px 0 10px;
            color: #34495e;
        }
        .computer-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }
        .computer-card {
            background: white;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 1px 4px rgba(0,0,0,0.05);
            transition: box-shadow 0.2s;
            display: flex;
            flex-direction: column;
            gap: 5px;
        }
        .computer-card:hover {
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        .computer-card strong {
            color: #34495e;
            font-size: 14px;
            margin-bottom: 2px;
        }
        .computer-card span {
            color: #555;
            word-break: break-word;
        }
        .disk-progress {
            margin-top: 5px;
            background-color: #f0f0f0;
            border-radius: 10px;
            height: 20px;
            width: 100%;
            overflow: hidden;
        }
        .disk-progress-bar {
            height: 100%;
            background-color: #4CAF50;
            text-align: center;
            line-height: 20px;
            color: white;
            font-size: 12px;
            font-weight: bold;
            white-space: nowrap;
            transition: width 0.3s;
        }
        .disk-progress-bar.warning {
            background-color: #ff9800;
        }
        .disk-progress-bar.danger {
            background-color: #f44336;
        }
        @media (max-width: 768px) {
            .computer-grid {
                grid-template-columns: 1fr;
            }
            .container {
                padding: 10px;
            }
        }
    </style>
    """

    # Начало HTML
    html_parts = []
    html_parts.append(f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Инвентаризация: {html.escape(hostname)}</title>
    {styles}
</head>
<body>
<div class="container">
    <h1>Отчёт о компьютере: {html.escape(hostname)}</h1>
    <p><strong>Дата сбора:</strong> {html.escape(collected_at)}</p>
""")

    # Блок "Аппаратное обеспечение"
    html_parts.append("""
    <div class="computer-section">
        <h3>Аппаратное обеспечение</h3>
        <div class="computer-grid">
""")
    # CPU
    html_parts.append(f"""
            <div class="computer-card">
                <strong>Процессор</strong>
                <span>{html.escape(str(cpu.get('model', 'N/A')))}</span>
                <span>Ядер: {cpu.get('cores', 'N/A')}, потоков: {cpu.get('threads', 'N/A')}</span>
                <span>Серийный номер: {html.escape(cpu.get('serial', 'N/A'))}</span>
                <span>Частота: {html.escape(cpu.get('max_speed', 'N/A'))}</span>
            </div>
""")
    # Материнская плата
    html_parts.append(f"""
            <div class="computer-card">
                <strong>Материнская плата</strong>
                <span>{html.escape(motherboard.get('model', 'N/A'))}</span>
                <span>Производитель: {html.escape(motherboard.get('manufacturer', 'N/A'))}</span>
                <span>Серийный номер: {html.escape(motherboard.get('serial', 'N/A'))}</span>
                <span>Слотов RAM: {motherboard.get('memory_slots', 'N/A')}</span>
            </div>
""")
    # GPU
    if gpu_list:
        for idx, gpu in enumerate(gpu_list, 1):
            html_parts.append(f"""
            <div class="computer-card">
                <strong>Видеокарта {idx}</strong>
                <span>{html.escape(gpu.get('name', 'N/A'))}</span>
                <span>Память: {gpu.get('memory_gb', 'N/A')} GB</span>
                <span>Драйвер: {html.escape(gpu.get('driver_version', 'N/A'))}</span>
                <span>Серийный номер: {html.escape(gpu.get('serial', 'N/A'))}</span>
            </div>
""")
    else:
        html_parts.append("""
            <div class="computer-card"><span>Видеокарты не обнаружены</span></div>
""")
    html_parts.append("        </div>\n")

    # RAM
    if ram_modules:
        html_parts.append(f"""
        <h4>Оперативная память (всего: {total_ram} GB, слотов: {memory_slots})</h4>
        <div class="computer-grid">
""")
        for mod in ram_modules:
            html_parts.append(f"""
            <div class="computer-card">
                <strong>Планка RAM</strong>
                <span>Производитель: {html.escape(mod.get('manufacturer', 'N/A'))}</span>
                <span>Объём: {mod.get('capacity', 0)} GB</span>
                <span>Серийный номер: {html.escape(mod.get('serial', 'N/A'))}</span>
            </div>
""")
        html_parts.append("        </div>\n")
    else:
        html_parts.append("<p>Нет данных об оперативной памяти</p>\n")

    # BIOS
    if bios:
        html_parts.append("""
        <h4>BIOS</h4>
        <div class="computer-grid">
""")
        html_parts.append(f"""
            <div class="computer-card">
                <strong>Версия BIOS</strong>
                <span>{html.escape(bios.get('SMBIOSBIOSVersion', 'N/A'))}</span>
                <span>Серийный номер: {html.escape(bios.get('SerialNumber', 'N/A'))}</span>
            </div>
""")
        html_parts.append("        </div>\n")

    html_parts.append("    </div>\n")  # закрытие computer-section

    # Блок "Накопители" (физические диски)
    if physical_disks:
        html_parts.append("""
    <div class="computer-section">
        <h3>Накопители</h3>
        <div class="computer-grid">
""")
        for disk in physical_disks:
            html_parts.append(f"""
            <div class="computer-card">
                <strong>Диск: {html.escape(disk.get('model', 'N/A'))}</strong>
                <span>Тип: {html.escape(disk.get('disk_type', 'N/A'))}</span>
                <span>Размер: {disk.get('size_gb', 0)} GB</span>
                <span>Серийный номер: {html.escape(disk.get('serial', 'N/A'))}</span>
            </div>
""")
        html_parts.append("        </div>\n    </div>\n")

    # Логические тома (все)
    if logical_disks:
        html_parts.append("""
    <div class="computer-section">
        <h3>Логические тома</h3>
        <div class="computer-grid">
""")
        for vol in logical_disks:
            size = vol.get('size_gb', 0)
            free = vol.get('free_gb', 0)
            used = size - free
            percent = round((used / size) * 100) if size > 0 else 0
            bar_class = ''
            if percent >= 90:
                bar_class = 'danger'
            elif percent >= 75:
                bar_class = 'warning'
            html_parts.append(f"""
            <div class="computer-card">
                <strong>Том: {html.escape(vol.get('drive', 'N/A'))}</strong>
                <span>Файловая система: {html.escape(vol.get('filesystem', 'N/A'))}</span>
                <span>Размер: {size} GB</span>
                <span>Свободно: {free} GB</span>
                <div class="disk-progress">
                    <div class="disk-progress-bar {bar_class}" style="width: {percent}%;">{percent}%</div>
                </div>
            </div>
""")
        html_parts.append("        </div>\n    </div>\n")

    # Блок "Сетевые интерфейсы"
    if network:
        html_parts.append("""
    <div class="computer-section">
        <h3>Сетевые интерфейсы</h3>
        <div class="computer-grid">
""")
        for adapter in network:
            html_parts.append(f"""
            <div class="computer-card">
                <strong>{html.escape(adapter.get('description', 'Адаптер'))}</strong>
                <span>MAC: {html.escape(adapter.get('mac_address', 'N/A'))}</span>
                <span>IPv4: {', '.join(html.escape(ip) for ip in adapter.get('ipv4', [])) or 'N/A'}</span>
                <span>IPv6: {', '.join(html.escape(ip) for ip in adapter.get('ipv6', [])) or 'N/A'}</span>
                <span>Шлюз: {html.escape(adapter.get('gateway', 'N/A'))}</span>
                <span>DNS: {', '.join(html.escape(dns) for dns in adapter.get('dns_servers', [])) or 'N/A'}</span>
                <span>DHCP: {html.escape(adapter.get('dhcp_enabled', 'N/A'))}</span>
            </div>
""")
        html_parts.append("        </div>\n    </div>\n")

    # Блок "Система"
    html_parts.append(f"""
    <div class="computer-section">
        <h3>Система</h3>
        <div class="computer-grid">
            <div class="computer-card">
                <strong>Hostname</strong>
                <span>{html.escape(hostname)}</span>
            </div>
            <div class="computer-card">
                <strong>Операционная система</strong>
                <span>{html.escape(os_info.get('pretty', 'N/A'))}</span>
            </div>
            <div class="computer-card">
                <strong>Дата сбора</strong>
                <span>{html.escape(collected_at)}</span>
            </div>
        </div>
    </div>
""")

    # Блок "Пользователи"
    if users:
        html_parts.append("""
    <div class="computer-section">
        <h3>Пользователи (последний вход)</h3>
        <div class="computer-grid">
""")
        for user, last in users.items():
            html_parts.append(f"""
            <div class="computer-card">
                <strong>{html.escape(user)}</strong>
                <span>{html.escape(last)}</span>
            </div>
""")
        html_parts.append("        </div>\n    </div>\n")

    html_parts.append("</div></body></html>")
    return "".join(html_parts)

# ---------------------------------------------------------
# ЛОГИКА ОГРАНИЧЕНИЙ И ОТПРАВКИ
# ---------------------------------------------------------
def check_rate_limit():
    now = time.time()
    runs = []
    if os.path.exists(LIMIT_FILE):
        try:
            with open(LIMIT_FILE, "r") as f: runs = json.load(f)
        except: pass
    recent = [r for r in runs if r > (now - 3600)]
    if len(recent) >= MAX_RUNS_PER_HOUR: return False
    recent.append(now)
    with open(LIMIT_FILE, "w") as f: json.dump(recent, f)
    return True

def send_email(data, html_content):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = RECIPIENT_EMAIL
    msg["Subject"] = f"Inventory Report: {data['hostname']}"

    # JSON вложение
    json_str = json.dumps(data, indent=4, ensure_ascii=False)
    json_attachment = MIMEText(json_str, "plain", "utf-8")
    json_attachment.add_header("Content-Disposition", "attachment", filename=f"{data['hostname']}.json")
    msg.attach(json_attachment)

    # HTML вложение
    html_attachment = MIMEText(html_content, "html", "utf-8")
    html_attachment.add_header("Content-Disposition", "attachment", filename=f"{data['hostname']}_report.html")
    msg.attach(html_attachment)

    try:
        with smtplib.SMTP_SSL("smtp.mail.ru", 465) as server:
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

# ---------------------------------------------------------
# ЗАПУСК
# ---------------------------------------------------------
if __name__ == "__main__":
    if check_rate_limit():
        full_data = gather_all()
        html_report = generate_html_report(full_data)
        send_email(full_data, html_report)
    sys.exit()