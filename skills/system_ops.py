import os
import shutil
import stat
import sys
from pathlib import Path

# Додаємо батьківську директорію для імпорту config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
CAPCUT_CACHE_PATH = str(config.CAPCUT_CACHE_PATH)

try:
    import winshell  # pip install winshell pypiwin32
except ImportError:
    winshell = None

# Допоміжна функція для прав доступу
def _remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clean_capcut_cache():
    """Чистка кешу CapCut"""
    # Використовуємо шлях з config.py
    cache_path = CAPCUT_CACHE_PATH
    
    print(f"🔍 Шукаю кеш тут: {cache_path}")
    
    if not os.path.exists(cache_path):
        return "Папка CapCut Cache не знайдена. Можливо, CapCut не встановлено або шлях інший."

    try:
        # Рахуємо розмір
        total_size = 0
        for dirpath, _, filenames in os.walk(cache_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
        
        size_mb = total_size / (1024 * 1024)
        
        if size_mb < 50:
            return f"Кеш занадто малий ({size_mb:.2f} MB), чистка не потрібна."
            
        print(f"🧹 Видаляю {size_mb:.2f} MB...")
        
        # Видалення
        for item in os.listdir(cache_path):
            item_path = os.path.join(cache_path, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path, onerror=_remove_readonly)
            except Exception as e:
                print(f"⚠️ Пропуск файлу: {e}")
                
        return f"Кеш CapCut успішно очищено. Звільнено {size_mb:.2f} MB."
        
    except Exception as e:
        return f"Помилка при доступі до файлів: {e}"

def empty_recycle_bin():
    """Очистка кошика"""
    if not winshell:
        return "Install winshell to use this feature: pip install winshell pypiwin32"
        
    try:
        winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
        return "Кошик очищено."
    except Exception:
        return "Кошик вже порожній."
