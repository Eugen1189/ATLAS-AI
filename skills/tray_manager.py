"""
skills/tray_manager.py
Менеджер системного трею для ATLAS.
Дозволяє згортати додаток в трей замість закриття.
"""

import sys
import threading
from pathlib import Path

# Спроба імпорту pystray
try:
    import pystray
    from PIL import Image, ImageDraw
    HAS_PYSTRAY = True
except ImportError:
    HAS_PYSTRAY = False
    pystray = None
    Image = None
    ImageDraw = None


class TrayManager:
    """
    Менеджер системного трею для ATLAS.
    
    Дозволяє:
    - Згортати додаток в трей
    - Показувати статус в треї
    - Швидкий доступ до функцій через контекстне меню
    """
    
    def __init__(self, on_show=None, on_quit=None):
        """
        Ініціалізація менеджера трею.
        
        Args:
            on_show: Callback для показу вікна
            on_quit: Callback для виходу з додатку
        """
        self.on_show = on_show
        self.on_quit = on_quit
        self.icon = None
        self.is_running = False
        
        if not HAS_PYSTRAY:
            print("[TRAY] pystray не встановлено. Встановіть: pip install pystray")
            return
        
        self._create_icon()
    
    def _create_icon(self):
        """Створює іконку для трею"""
        if not HAS_PYSTRAY:
            return
        
        try:
            # Створюємо просту іконку (16x16 пікселів)
            # Якщо є файл іконки - використовуємо його
            icon_path = Path("assets/atlas_icon.png")
            if icon_path.exists():
                image = Image.open(icon_path)
                # Змінюємо розмір до 16x16 для трею
                image = image.resize((16, 16), Image.Resampling.LANCZOS)
            else:
                # Створюємо просту іконку програмно
                image = Image.new('RGB', (16, 16), color='cyan')
                draw = ImageDraw.Draw(image)
                # Малюємо простий символ "A" для ATLAS
                draw.text((4, 2), "A", fill='white')
            
            # Створюємо меню
            menu = pystray.Menu(
                pystray.MenuItem("Показати ATLAS", self._show_window, default=True),
                pystray.MenuItem("Статус", self._show_status),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Вихід", self._quit_app)
            )
            
            self.icon = pystray.Icon(
                "ATLAS",
                image,
                "ATLAS SystemCOO",
                menu
            )
            
        except Exception as e:
            print(f"[TRAY] Помилка створення іконки: {e}")
            self.icon = None
    
    def _show_window(self, icon=None, item=None):
        """Показує головне вікно"""
        if self.on_show:
            self.on_show()
    
    def _show_status(self, icon=None, item=None):
        """Показує статус системи"""
        if self.on_show:
            self.on_show()
        # Можна додати показ статусу через notification
    
    def _quit_app(self, icon=None, item=None):
        """Вихід з додатку"""
        if self.on_quit:
            self.on_quit()
        self.stop()
    
    def start(self):
        """Запускає іконку в треї"""
        if not HAS_PYSTRAY:
            print("[TRAY] pystray не встановлено. Трей недоступний.")
            return
        
        if self.icon and not self.is_running:
            self.is_running = True
            # Запускаємо в окремому потоці
            threading.Thread(target=self.icon.run, daemon=True).start()
            print("[TRAY] Іконка в треї запущена")
    
    def stop(self):
        """Зупиняє іконку в треї"""
        if self.icon and self.is_running:
            self.is_running = False
            self.icon.stop()
            print("[TRAY] Іконка в треї зупинена")
    
    def notify(self, title, message):
        """
        Показує сповіщення з трею.
        
        Args:
            title: Заголовок сповіщення
            message: Текст сповіщення
        """
        if self.icon:
            try:
                self.icon.notify(message, title=title)
            except Exception as e:
                print(f"[TRAY] Помилка сповіщення: {e}")


def setup_autostart():
    """
    Налаштовує автозапуск ATLAS разом з Windows.
    
    Створює ярлик в папці автозапуску Windows.
    """
    import os
    import win32com.client
    
    try:
        # Шлях до скрипта запуску
        script_path = Path(__file__).parent.parent / "main_with_atlas.py"
        if not script_path.exists():
            print("[AUTOSTART] Файл main_with_atlas.py не знайдено")
            return False
        
        # Шлях до папки автозапуску
        startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        startup_folder.mkdir(parents=True, exist_ok=True)
        
        # Створюємо ярлик
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut_path = startup_folder / "ATLAS.lnk"
        shortcut = shell.CreateShortCut(str(shortcut_path))
        shortcut.TargetPath = sys.executable
        shortcut.Arguments = f'"{script_path}"'
        shortcut.WorkingDirectory = str(script_path.parent)
        shortcut.IconLocation = sys.executable  # Використовуємо іконку Python
        shortcut.save()
        
        print(f"[AUTOSTART] Ярлик створено: {shortcut_path}")
        return True
        
    except ImportError:
        print("[AUTOSTART] win32com не встановлено. Встановіть: pip install pywin32")
        return False
    except Exception as e:
        print(f"[AUTOSTART] Помилка налаштування автозапуску: {e}")
        return False


def remove_autostart():
    """Видаляє автозапуск ATLAS"""
    import os
    
    try:
        startup_folder = Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        shortcut_path = startup_folder / "ATLAS.lnk"
        
        if shortcut_path.exists():
            shortcut_path.unlink()
            print(f"[AUTOSTART] Ярлик видалено: {shortcut_path}")
            return True
        else:
            print("[AUTOSTART] Ярлик не знайдено")
            return False
            
    except Exception as e:
        print(f"[AUTOSTART] Помилка видалення автозапуску: {e}")
        return False
