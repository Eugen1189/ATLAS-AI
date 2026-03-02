import os
import subprocess
import time
import sys
import pyautogui
import pyperclip
from pathlib import Path

# Додаємо батьківську директорію для імпорту config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import config
except ImportError:
    import collections
    config = collections.namedtuple('config', ['CURSOR_EXE_PATH'])(CURSOR_EXE_PATH='')

class CursorAgent:
    def __init__(self):
        # Шлях до Cursor (використовуємо динамічний шлях з config)
        self.cursor_path = str(config.CURSOR_EXE_PATH)

    def focus_cursor(self):
        """Робить вікно Cursor активним"""
        print("🖱️ [CURSOR AGENT] Перемикаю фокус...")
        
        # Найпростіший спосіб активувати вікно - запустити його знову.
        # Windows просто перекине нас на вже відкрите вікно (os.startfile безпечніший за Popen).
        if os.path.exists(self.cursor_path):
            try:
                os.startfile(self.cursor_path)
                time.sleep(1)  # Чекаємо поки вікно випливе
                return True
            except Exception as e:
                print(f"❌ [CURSOR AGENT] Помилка фокусування: {e}")
                return False
        return False

    def send_prompt(self, prompt_text, mode="chat"):
        """
        Відправляє промпт у Cursor.
        mode="chat" -> Ctrl+L (Бічний чат)
        mode="composer" -> Ctrl+I (Composer - якщо увімкнено)
        """
        if not self.focus_cursor():
            return "Не знайшов Cursor.exe"

        print(f"🤖 [CURSOR AGENT] Пишу код...")

        # 1. Відкриваємо панель AI
        if mode == "chat":
            pyautogui.hotkey('ctrl', 'l')  # Відкрити Chat
        elif mode == "composer":
            pyautogui.hotkey('ctrl', 'i')  # Відкрити Composer (Beta)
        
        time.sleep(0.5)

        # 2. Очищаємо поле (на всяк випадок, якщо там щось було)
        # Ctrl+A -> Backspace
        # pyautogui.hotkey('ctrl', 'a')
        # pyautogui.press('backspace')

        # 3. Вставляємо текст через буфер обміну (швидко і надійно)
        pyperclip.copy(prompt_text)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.5)

        # 4. Відправляємо
        pyautogui.press('enter')
        
        return "Завдання передано в Cursor."



