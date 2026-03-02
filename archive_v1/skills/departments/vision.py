"""
skills/departments/vision.py
Департамент Зору: Скріншоти, Сканування системи.
"""

import sys
import os
from pathlib import Path
import pyautogui
import datetime

# Додаємо шлях для імпортів
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from .base import Department

# Спроба імпорту scanner (для діагностики)
try:
    from skills.scanner import scan_system
    HAS_SCANNER = True
except ImportError:
    HAS_SCANNER = False

class VisionDepartment(Department):
    def __init__(self):
        super().__init__("Vision", priority=3)
        
        # Папка для скріншотів (з config)
        import config
        self.screenshots_dir = config.SCREENSHOTS_DIR
        self.screenshots_dir.mkdir(exist_ok=True, parents=True)
        self.navigator = None # Lazy init

    def _get_navigator(self):
        if not self.navigator:
            from skills.system_navigator import SystemNavigator
            self.navigator = SystemNavigator()
        return self.navigator

    def can_handle(self, query: str) -> bool:
        # Router зазвичай робить це через Override, але про всяк випадок:
        triggers = ["скріншот", "скрін", "скануй систему", "що на екрані", "діагностика"]
        return any(t in query.lower() for t in triggers)

    def handle(self, query: str, context=None) -> str:
        query_lower = query.lower()

        # 0. 👁️ АКТИВАЦІЯ ЖЕСТІВ (Повертаємо спеціальну команду для Router/ScenarioManager)
        gestures_triggers = ["візуальне", "жести", "камеру", "vision", "руки", "курсор", "клік", "зум"]
        if any(t in query_lower for t in gestures_triggers):
            # Ця команда буде перехоплена в ScenarioManager або AtlasCore
            # Але якщо ми тут, Router вже викликав нас.
            # Нам потрібно повернути інструкцію "Запусти VisionManager"
            return "INTERNAL:vision:start"

        # 1. 🔍 СИСТЕМНЕ СКАНУВАННЯ
        if "скануй" in query_lower or "діагностика" in query_lower:
            if HAS_SCANNER:
                return scan_system() # Викликає наш сканер і повертає текст звіту
            return "Помилка: модуль scanner.py не знайдено."

        # 2. 📸 СКРІНШОТ
        if "скрін" in query_lower or "screen" in query_lower:
            return self._take_screenshot()

        # 3. 🛡️ VERIFY FOCUS (Перевірка фокусу)
        if "перевір фокус" in query_lower or "verify focus" in query_lower or "що активно" in query_lower:
             return self.verify_active_window()

        return "Команда Vision не розпізнана."

    def verify_active_window(self) -> str:
        """Перевіряє активне вікно через SystemNavigator."""
        try:
            nav = self._get_navigator()
            ui_tree = nav.get_active_window_ui()
            
            # ui_tree is a list of distinct elements. The first one is usually the window or main container.
            if not ui_tree:
                return "⚠️ Не можу визначити активне вікно (можливо, робочий стіл)."
            
            # Find the window name (first element typically)
            window_name = ui_tree[0].get('Name', 'Unknown')
            
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            return f"👁️ [VISION] Активне вікно: '{window_name}'. Готовий до роботи."
            
        except Exception as e:
            return f"❌ Помилка перевірки фокусу: {e}"

    def _take_screenshot(self) -> str:
        """Робить скріншот і зберігає його"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"screenshot_{timestamp}.png"
            path = self.screenshots_dir / filename
            
            # Робимо скріншот
            screenshot = pyautogui.screenshot()
            screenshot.save(path)
            
            return f"Скріншот збережено: {path}"
        except Exception as e:
            return f"Помилка створення скріншота: {e}"

    def start(self, query: str = "", context=None) -> str:
        """Повертає команду для запуску VisionManager через AtlasCore"""
        return "INTERNAL:vision:start"

    def stop(self, query: str = "", context=None) -> str:
        """Повертає команду для зупинки VisionManager через AtlasCore"""
        return "INTERNAL:vision:stop"
