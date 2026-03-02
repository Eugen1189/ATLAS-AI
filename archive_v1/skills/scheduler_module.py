"""
skills/scheduler_module.py
Модуль "Ранковий Протокол" (Scheduler) для проактивних зведень ATLAS.

Автоматично надсилає голосові зведення:
- Погода на день
- Дедлайни з Memory
- Курс валют / Новини
- Стан системи (батарея, CPU, RAM)
- Мотиваційна фраза
"""

import threading
import time
import datetime
import schedule
import sys
from pathlib import Path
from typing import Optional

# Додаємо батьківську директорію для імпортів
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config

# Імпорти для збору даних
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[SCHEDULER] psutil не встановлено. Стан системи недоступний.")

# Імпорт для пошуку в інтернеті
try:
    from skills.tools_definition import execute_tool
    HAS_WEB_SEARCH = True
except ImportError:
    HAS_WEB_SEARCH = False
    print("[SCHEDULER] Web search недоступний.")

# Імпорт для голосового виходу
try:
    from skills.voice_output import text_to_speech_file, HAS_OPENAI_TTS
except ImportError:
    HAS_OPENAI_TTS = False
    print("[SCHEDULER] Голосовий вихід недоступний.")

# Імпорт Journal для отримання дедлайнів
try:
    from skills.journal import Journal
    HAS_JOURNAL = True
except ImportError:
    HAS_JOURNAL = False
    print("[SCHEDULER] Journal недоступний.")


class MorningBriefingScheduler:
    """
    Планувальник для автоматичних ранкових зведень.
    """
    
    def __init__(self, telegram_bridge=None, atlas_core=None):
        """
        Ініціалізація Scheduler.
        
        Args:
            telegram_bridge: Екземпляр TelegramBridge для надсилання повідомлень
            atlas_core: Екземпляр AtlasCore для доступу до Brain/Oracle
        """
        self.telegram_bridge = telegram_bridge
        self.atlas_core = atlas_core
        self.journal = Journal() if HAS_JOURNAL else None
        self.running = False
        self.thread = None
        
        print("[SCHEDULER] Ініціалізовано")
    
    def start(self, briefing_time="09:00"):
        """
        Запускає планувальник.
        
        Args:
            briefing_time: Час ранкового зведення (формат "HH:MM")
        """
        if self.running:
            print("[SCHEDULER] Вже запущено")
            return
        
        self.running = True
        
        # Плануємо ранкове зведення
        schedule.every().day.at(briefing_time).do(self._send_morning_briefing)
        
        # Запускаємо потік для обробки розкладу
        self.thread = threading.Thread(target=self._schedule_loop, daemon=True)
        self.thread.start()
        
        print(f"[SCHEDULER] Запущено. Ранкове зведення о {briefing_time}")
    
    def stop(self):
        """Зупиняє планувальник"""
        self.running = False
        schedule.clear()
        if self.thread:
            self.thread.join(timeout=2)
        print("[SCHEDULER] Зупинено")
    
    def _schedule_loop(self):
        """Головний цикл обробки розкладу"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Перевірка кожну хвилину
    
    def send_briefing_now(self):
        """Надсилає зведення зараз (для тестування або при старті)"""
        self._send_morning_briefing()
    
    def _send_morning_briefing(self):
        """Генерує та надсилає ранкове зведення"""
        try:
            print("[SCHEDULER] Генерую ранкове зведення...")
            
            # Збираємо дані
            briefing_parts = []
            
            # 1. Привітання
            current_hour = datetime.datetime.now().hour
            if 5 <= current_hour < 12:
                greeting = "Доброго ранку"
            elif 12 <= current_hour < 18:
                greeting = "Доброго дня"
            elif 18 <= current_hour < 22:
                greeting = "Доброго вечора"
            else:
                greeting = "Доброї ночі"
            
            briefing_parts.append(f"{greeting}, Сер. Ось ваше зведення на сьогодні.")
            
            # 2. Погода
            weather_info = self._get_weather()
            if weather_info:
                briefing_parts.append(f"\nПогода: {weather_info}")
            
            # 3. Дедлайни
            deadlines = self._get_deadlines()
            if deadlines:
                briefing_parts.append(f"\nДедлайни: {deadlines}")
            
            # 4. Курс валют
            currency_info = self._get_currency()
            if currency_info:
                briefing_parts.append(f"\nКурс валют: {currency_info}")
            
            # 5. Стан системи
            system_status = self._get_system_status()
            if system_status:
                briefing_parts.append(f"\nСтан системи: {system_status}")
            
            # 6. Мотиваційна фраза
            motivation = self._get_motivation()
            if motivation:
                briefing_parts.append(f"\n{motivation}")
            
            # Формуємо фінальний текст
            briefing_text = "\n".join(briefing_parts)
            
            # Надсилаємо через Telegram
            if self.telegram_bridge and self.telegram_bridge.bot:
                self._send_via_telegram(briefing_text)
            else:
                print(f"[SCHEDULER] Зведення:\n{briefing_text}")
            
        except Exception as e:
            print(f"[SCHEDULER] Помилка генерації зведення: {e}")
            import traceback
            traceback.print_exc()
    
    def _get_weather(self) -> Optional[str]:
        """Отримує інформацію про погоду"""
        if not HAS_WEB_SEARCH:
            return None
        
        try:
            # Визначаємо місто (можна додати в config)
            city = getattr(config, 'WEATHER_CITY', 'Київ')
            query = f"погода в {city} сьогодні"
            
            # Використовуємо web_search через execute_tool з контекстом
            context = None
            if self.atlas_core and hasattr(self.atlas_core, 'brain') and hasattr(self.atlas_core.brain, 'router'):
                context = self.atlas_core.brain.router.context
                
            result = execute_tool("web_search", {"query": query}, context)
            
            if result and "❌" not in result:
                # Обрізаємо довгий результат
                if len(result) > 200:
                    result = result[:200] + "..."
                return result
        except Exception as e:
            print(f"[SCHEDULER] Помилка отримання погоди: {e}")
        
        return None
    
    def _get_deadlines(self) -> Optional[str]:
        """Отримує дедлайни з Journal"""
        if not self.journal:
            return None
        
        try:
            # Шукаємо в папці "Deadlines" або "Tasks"
            deadlines = self.journal.read_category("Deadlines", limit=5)
            if not deadlines:
                deadlines = self.journal.read_category("Tasks", limit=5)
            
            if deadlines:
                # Обрізаємо довгий текст
                if len(deadlines) > 300:
                    deadlines = deadlines[:300] + "..."
                return deadlines
        except Exception as e:
            print(f"[SCHEDULER] Помилка отримання дедлайнів: {e}")
        
        return "Немає активних дедлайнів на сьогодні."
    
    def _get_currency(self) -> Optional[str]:
        """Отримує курс валют"""
        if not HAS_WEB_SEARCH:
            return None
        
        try:
            query = "курс долара та євро до гривні сьогодні"
            # Використовуємо web_search через execute_tool з контекстом
            context = None
            if self.atlas_core and hasattr(self.atlas_core, 'brain') and hasattr(self.atlas_core.brain, 'router'):
                context = self.atlas_core.brain.router.context
                
            result = execute_tool("web_search", {"query": query}, context)
            
            if result and "❌" not in result:
                if len(result) > 200:
                    result = result[:200] + "..."
                return result
        except Exception as e:
            print(f"[SCHEDULER] Помилка отримання курсу валют: {e}")
        
        return None
    
    def _get_system_status(self) -> Optional[str]:
        """Отримує стан системи"""
        if not HAS_PSUTIL:
            return None
        
        try:
            status_parts = []
            
            # CPU
            cpu_percent = psutil.cpu_percent(interval=1)
            status_parts.append(f"CPU: {cpu_percent:.1f}%")
            
            # RAM
            ram = psutil.virtual_memory()
            ram_percent = ram.percent
            ram_free_gb = ram.available / (1024**3)
            status_parts.append(f"RAM: {ram_percent:.1f}% (вільно {ram_free_gb:.1f} GB)")
            
            # Battery (якщо ноутбук)
            battery = psutil.sensors_battery()
            if battery:
                battery_percent = battery.percent
                is_plugged = battery.power_plugged
                status = "на зарядці" if is_plugged else "не на зарядці"
                status_parts.append(f"Батарея: {battery_percent:.0f}% ({status})")
            
            # Disk space
            disk = psutil.disk_usage('/')
            disk_free_gb = disk.free / (1024**3)
            disk_percent = disk.percent
            status_parts.append(f"Диск: {disk_percent:.1f}% зайнято (вільно {disk_free_gb:.1f} GB)")
            
            return ", ".join(status_parts)
        except Exception as e:
            print(f"[SCHEDULER] Помилка отримання стану системи: {e}")
        
        return None
    
    def _get_motivation(self) -> Optional[str]:
        """Генерує мотиваційну фразу"""
        motivations = [
            "Гарного дня та продуктивної роботи!",
            "Сьогодні буде чудовий день для досягнень.",
            "Вдалого кодингу та натхнення!",
            "Готовий допомогти з будь-якими завданнями.",
            "Бажаю успіхів у всіх проектах сьогодні."
        ]
        
        import random
        return random.choice(motivations)
    
    def _send_via_telegram(self, text: str):
        """Надсилає зведення через Telegram з голосовим повідомленням"""
        if not self.telegram_bridge or not self.telegram_bridge.bot:
            return
        
        try:
            # Отримуємо chat_id з config або використовуємо перший з ALLOWED_USER_IDS
            chat_id = getattr(config, 'TELEGRAM_CHAT_ID', None)
            if not chat_id:
                # Fallback: використовуємо перший дозволений user ID
                allowed_ids = getattr(config, 'ALLOWED_USER_IDS', [])
                if allowed_ids:
                    chat_id = allowed_ids[0]
                    print(f"[SCHEDULER] Використовую chat_id з ALLOWED_USER_IDS: {chat_id}")
                else:
                    print("[SCHEDULER] TELEGRAM_CHAT_ID не встановлено і немає ALLOWED_USER_IDS")
                    return
            
            # Конвертуємо chat_id в int (Telegram API очікує число)
            try:
                chat_id = int(chat_id)
            except (ValueError, TypeError):
                print(f"[SCHEDULER] Помилка конвертації chat_id в число: {chat_id}")
                return
            
            # Генеруємо голосове повідомлення
            if HAS_OPENAI_TTS:
                audio_path = text_to_speech_file(text)
                if audio_path:
                    with open(audio_path, 'rb') as voice_file:
                        self.telegram_bridge.bot.send_voice(chat_id, voice_file)
                    print("[SCHEDULER] Голосове зведення надіслано")
            
            # Надсилаємо текст
            self.telegram_bridge.bot.send_message(
                chat_id,
                f"🌅 Ранкове зведення ATLAS\n\n{text}",
                parse_mode='HTML'
            )
            print("[SCHEDULER] Текстове зведення надіслано")
            
        except Exception as e:
            print(f"[SCHEDULER] Помилка надсилання через Telegram: {e}")
            import traceback
            traceback.print_exc()
