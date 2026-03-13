import threading
import time
import psutil
from agent_skills.telegram_bridge.manifest import send_telegram_message

def telemetry_loop():
    """Фоновий цикл моніторингу, що працює 24/7"""
    
    # Налаштування порогів чутливості
    CPU_THRESHOLD = 90.0  # Тривога, якщо CPU > 90%
    RAM_THRESHOLD = 85.0  # Тривога, якщо RAM > 85%
    CHECK_INTERVAL = 30   # Перевіряти кожні 30 секунд
    COOLDOWN = 300        # Після тривоги мовчати 5 хвилин, щоб не спамити
    
    while True:
        try:
            # Зчитуємо показники
            cpu_usage = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            ram_usage = ram.percent
            
            if cpu_usage > CPU_THRESHOLD or ram_usage > RAM_THRESHOLD:
                # 1. Ініціалізація замірів (psutil потребує двох кроків для точності)
                for p in psutil.process_iter(['name']):
                    try:
                        p.cpu_percent(interval=None)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                time.sleep(0.5) # Даємо системі півсекунди для збору точних даних
                
                # 2. Збираємо реальні дані, ігноруючи системні процеси-привиди
                processes = []
                ignore_list = ['System Idle Process', 'System', 'Registry', 'svchost.exe', '']
                
                for p in psutil.process_iter(['name', 'memory_percent']):
                    try:
                        name = p.info['name']
                        if name and name not in ignore_list:
                            cpu_p = p.cpu_percent(interval=None)
                            mem_p = p.info['memory_percent'] or 0.0
                            processes.append({'name': name, 'cpu': cpu_p, 'mem': mem_p})
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                        
                # 3. Сортуємо по реальному завантаженню CPU
                top_processes = sorted(processes, key=lambda p: p['cpu'], reverse=True)[:3]
                
                # Формуємо екстрений рапорт
                msg = "⚠️ <b>[АЛАРМ] Критичне навантаження системи!</b>\n\n"
                msg += f"🖥 <b>CPU:</b> {cpu_usage}%\n"
                msg += f"🧠 <b>RAM:</b> {ram_usage}%\n\n"
                msg += "🔥 <b>Топ процеси:</b>\n"
                
                for p in top_processes:
                    msg += f"• <code>{p['name']}</code>: CPU {p['cpu']:.1f}% | RAM {p['mem']:.1f}%\n"
                    
                msg += "\n<i>Командоре, використайте інструмент terminal_operator, щоб вбити ці процеси.</i>"
                
                # AXIS ініціює контакт першим!
                send_telegram_message(text=msg)
                
                # Засинаємо, щоб не закидати телефон повідомленнями
                time.sleep(COOLDOWN)
            else:
                time.sleep(CHECK_INTERVAL)
                
        except Exception as e:
            print(f"[Telemetry Error] Збій сенсорів: {e}")
            time.sleep(60)

def start_telemetry_daemon():
    """Запускає моніторинг у незалежному потоці (Thread)"""
    t = threading.Thread(target=telemetry_loop, daemon=True)
    t.start()
    print("[Telemetry] Автономний моніторинг системи УВІМКНЕНО. Працюю у фоні.")
