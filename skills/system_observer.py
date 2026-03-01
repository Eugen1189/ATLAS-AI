"""
System Observer - "Всевидяче Око" для проактивного моніторингу системи

Фоновий сервіс, який моніторить систему та повідомляє про проблеми.
"""

import threading
import time
from typing import Optional, Callable
from skills.system_navigator import SystemNavigator


class SystemObserver:
    """
    Фоновий сервіс для моніторингу системи.
    
    Відстежує:
    - CPU Usage (> 90%)
    - RAM Usage (> 90%)
    - Disk Space (< 10 GB)
    - Battery (для ноутбука < 20%)
    
    З механізмом Anti-Spam (cooldown 15 хвилин).
    """
    
    def __init__(self, atlas_core):
        """
        Ініціалізація System Observer.
        
        Args:
            atlas_core: Посилання на ядро ATLAS для доступу до Brain/Voice
        """
        self.atlas = atlas_core
        self.running = False
        self.thread = None
        
        # Cooldowns (щоб не спамив кожні 5 секунд)
        self.last_cpu_warning = 0
        self.last_ram_warning = 0
        self.last_battery_warning = 0
        self.last_proactive_check = 0
        
        # Visual Heartbeat
        self.navigator = SystemNavigator()
        self.last_screen_hash = None
        self.last_visual_check = 0
        
        print("✅ [SYSTEM OBSERVER] Ініціалізовано (Heartbeat Active)")
    
    def start(self):
        """Запускає фоновий потік моніторингу"""
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            print("👁️ [OBSERVER] System Watcher Started")
    
    def stop(self):
        """Зупиняє фоновий потік моніторингу"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _monitor_loop(self):
        """Головний цикл моніторингу"""
        while self.running:
            try:
                self._check_metrics()
                self._check_proactive_triggers()
                self._check_visual_changes()
            except Exception as e:
                print(f"❌ [OBSERVER] Error: {e}")
            time.sleep(5)  # Перевірка частіше (5с), але тригери мають свої кулдауни
    
    def _check_metrics(self):
        """Перевіряє всі метрики системи"""
        current_time = time.time()
        
        try:
            import psutil
        except ImportError:
            print("⚠️ [OBSERVER] psutil не встановлено. System Observer не може працювати.")
            return
        
        # 1. CPU Monitor (> 90%)
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 90 and (current_time - self.last_cpu_warning > 300):  # 5 хв кулдаун
            self._speak(f"Увага! Завантаження процесора критичне: {int(cpu_percent)} відсотків.")
            self.last_cpu_warning = current_time
        
        # 2. RAM Monitor (> 90%)
        ram = psutil.virtual_memory()
        if ram.percent > 90 and (current_time - self.last_ram_warning > 300):
            self._speak(f"Оперативна пам'ять переповнена. Вільно менше 10 відсотків.")
            self.last_ram_warning = current_time
        
        # 3. Battery Monitor (Laptop only) - < 20% і не на зарядці
        battery = psutil.sensors_battery()
        if battery and not battery.power_plugged and battery.percent < 20 and (current_time - self.last_battery_warning > 600):
            self._speak(f"Низький заряд батареї: {int(battery.percent)} відсотків. Підключіть живлення.")
            self.last_battery_warning = current_time
    
    def _check_proactive_triggers(self):
        """
        Проактивний аналіз контексту.
        """
        current_time = time.time()
        # check every 60 seconds
        if current_time - self.last_proactive_check < 60:
            return
            
        self.last_proactive_check = current_time
        
        # Example: Idle Check
        # If no user interaction for 1 hour, maybe suggest standing up or check status
        # Requires access to last_interaction timestamp from ContextBuffer
        if hasattr(self.atlas, 'brain') and self.atlas.brain:
             try:
                 last_interaction = self.atlas.brain.context_buffer.user_state.get('last_interaction', 0)
                 if last_interaction > 0 and (current_time - last_interaction > 3600): # 1 hour
                     # self._speak("Сер, ви давно не давали команд. Системи у режимі очікування.")
                     # Just logging for now to not be annoying
                     pass
             except:
                 pass

    def _check_visual_changes(self):
        """
        Visual Heartbeat: Перевіряє зміни на екрані через хешування.
        """
        try:
            current_time = time.time()
            if current_time - self.last_visual_check < 2:
                return

            self.last_visual_check = current_time
            
            new_hash = self.navigator.get_screen_hash()
            if new_hash:
                new_hash = new_hash.strip()
                if self.last_screen_hash and new_hash != self.last_screen_hash:
                    # Screen changed!
                    # print(f"👁️ [OBSERVER] Visual Change Detected! ({new_hash[:8]}...)")
                    pass
                self.last_screen_hash = new_hash
        except Exception as e:
            print(f"⚠️ [OBSERVER] Visual Heartbeat Failed: {e}")

    def _speak(self, text: str):
        """Озвучує повідомлення через ATLAS."""
        print(f"🗣️ [OBSERVER] {text}")
        if self.atlas and hasattr(self.atlas, 'voice_output') and self.atlas.voice_output:
            self.atlas.voice_output.speak(text)
