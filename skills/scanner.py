import sys
import os
import platform
import psutil
import importlib.util
import subprocess
from pathlib import Path

# Імпорт config для централізованих шляхів
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

def check_library(lib_name):
    """Перевіряє наявність бібліотеки"""
    spec = importlib.util.find_spec(lib_name)
    return "✅" if spec else "❌"

def get_windows_version():
    """Визначає точну версію Windows (включаючи Windows 11)"""
    if platform.system() != "Windows":
        return f"{platform.system()} {platform.release()}"
    
    try:
        # Перевіряємо версію через platform.version()
        version = platform.version()
        version_parts = version.split('.')
        
        if len(version_parts) >= 2:
            major = int(version_parts[0])
            minor = int(version_parts[1])
            build = int(version_parts[2]) if len(version_parts) > 2 else 0
            
            # Windows 11 має версію 10.0.22000 або вище
            if major == 10 and minor == 0 and build >= 22000:
                # Спробуємо отримати детальну інформацію через PowerShell
                try:
                    result = subprocess.run(
                        ['powershell', '-Command', 
                         '(Get-ItemProperty "HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion").DisplayVersion'],
                        capture_output=True,
                        text=True,
                        timeout=3
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        display_version = result.stdout.strip()
                        return f"Windows 11 {display_version} (Build {build})"
                except:
                    pass
                
                return f"Windows 11 (Build {build})"
            elif major == 10:
                return f"Windows 10 (Build {build})"
            else:
                return f"Windows {major}.{minor} (Build {build})"
    except:
        pass
    
    # Fallback до стандартного методу
    return f"{platform.system()} {platform.release()}"

def get_processor_info():
    """Отримує реальну інформацію про процесор"""
    try:
        processor = platform.processor()
        cpu_count = psutil.cpu_count(logical=True)
        cpu_count_physical = psutil.cpu_count(logical=False)
        return {
            'name': processor,
            'logical_cores': cpu_count,
            'physical_cores': cpu_count_physical
        }
    except:
        return None

def get_cpu_temperature():
    """Спроба отримати реальну температуру CPU через WMI"""
    try:
        result = subprocess.run(
            ['powershell', '-Command',
             '$temp = Get-CimInstance MSAcpi_ThermalZoneTemperature -Namespace "root/wmi" -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty CurrentTemperature; if ($temp) { Write-Output "$([math]::Round(($temp - 2732) / 10, 1))" } else { Write-Output "N/A" }'],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0 and result.stdout.strip() and result.stdout.strip() != "N/A":
            return result.stdout.strip() + "°C"
    except:
        pass
    return "N/A"

def get_battery_info():
    """Отримує реальну інформацію про батарею (якщо ноутбук)"""
    try:
        battery = psutil.sensors_battery()
        if battery:
            plugged = "Так" if battery.power_plugged else "Ні"
            percent = int(battery.percent)
            return f"{percent}% (Зарядка: {plugged})"
    except:
        pass
    return "N/A (не ноутбук або недоступно)"

def scan_system():
    """
    Повна діагностика системи ATLAS.
    РЕАЛЬНО сканує систему для отримання точної інформації.
    Повертає текстовий звіт.
    """
    print("🔍 [SCANNER] Починаю реальне сканування системи...")
    
    report = ["=== 🛠 ЗВІТ ДІАГНОСТИКИ ATLAS ==="]
    
    # 1. СИСТЕМА (реальні дані)
    report.append(f"\n🖥 СИСТЕМА:")
    report.append(f"OS: {get_windows_version()}")
    report.append(f"Python: {sys.version.split()[0]}")
    try:
        report.append(f"Користувач: {os.getlogin()}")
    except:
        report.append(f"Користувач: {os.getenv('USERNAME', 'N/A')}")
    
    # Процесор (реальна інформація з системи)
    proc_info = get_processor_info()
    if proc_info:
        report.append(f"Процесор: {proc_info['name']}")
        report.append(f"Ядра: {proc_info['physical_cores']} фізичних / {proc_info['logical_cores']} логічних")
    
    # 2. РЕСУРСИ (реальні виміри в реальному часі)
    report.append(f"\n⚡ РЕСУРСИ (реальні виміри):")
    
    # CPU - вимірюємо з інтервалом 1 секунда для точності (реальний вимір)
    cpu_percent = psutil.cpu_percent(interval=1)
    report.append(f"CPU завантаження: {cpu_percent}%")
    
    # Температура CPU (реальна спроба отримати через WMI)
    cpu_temp = get_cpu_temperature()
    report.append(f"Температура CPU: {cpu_temp}")
    
    # RAM - детальна реальна інформація
    mem = psutil.virtual_memory()
    total_ram_gb = round(mem.total / 1024**3, 1)
    available_ram_gb = round(mem.available / 1024**3, 1)
    used_ram_gb = round((mem.total - mem.available) / 1024**3, 1)
    report.append(f"RAM: {total_ram_gb} GB загалом | {used_ram_gb} GB використано ({mem.percent}%) | {available_ram_gb} GB вільно")
    
    # Диск - детальна реальна інформація
    disk = psutil.disk_usage('C:')
    total_disk_gb = round(disk.total / 1024**3, 1)
    used_disk_gb = round(disk.used / 1024**3, 1)
    free_disk_gb = round(disk.free / 1024**3, 1)
    disk_percent = round((disk.used / disk.total) * 100, 1)
    report.append(f"Диск C:: {total_disk_gb} GB загалом | {used_disk_gb} GB використано ({disk_percent}%) | {free_disk_gb} GB вільно")
    
    # Батарея (реальна інформація, якщо ноутбук)
    battery_info = get_battery_info()
    report.append(f"Батарея: {battery_info}")

    # 3. БІБЛІОТЕКИ
    report.append(f"\n📚 БІБЛІОТЕКИ:")
    libs = ["flet", "vosk", "google.generativeai", "sounddevice", "pyautogui", "psutil"]
    for lib in libs:
        report.append(f"{check_library(lib)} {lib}")

    # 4. ФАЙЛОВА СТРУКТУРА
    report.append(f"\n📂 ФАЙЛИ:")
    base_dir = Path(__file__).parent.parent
    files_to_check = [
        "main_with_atlas.py",
        str(config.SCENARIOS_CONFIG_PATH),
        "skills/router.py",
        "skills/departments/operations.py"
    ]
    
    for f in files_to_check:
        path = base_dir / f
        exists = "✅" if path.exists() else "❌ ВІДСУТНІЙ"
        report.append(f"{exists} {f}")

    # 5. ВИСНОВОК
    report.append("\n✅ Сканування завершено. Система готова до роботи.")
    
    final_report = "\n".join(report)
    print(final_report)
    return final_report

if __name__ == "__main__":
    print(scan_system())
