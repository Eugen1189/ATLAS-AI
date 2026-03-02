"""
setup_autostart.py
Скрипт для налаштування автозапуску ATLAS разом з Windows.
"""

import sys
from pathlib import Path

# Додаємо батьківську директорію для імпортів
sys.path.insert(0, str(Path(__file__).resolve().parent))

from skills.tray_manager import setup_autostart, remove_autostart

if __name__ == "__main__":
    print("=" * 50)
    print("ATLAS - Налаштування автозапуску")
    print("=" * 50)
    print()
    
    choice = input("Виберіть дію:\n1. Додати автозапуск\n2. Видалити автозапуск\nВведіть номер (1 або 2): ")
    
    if choice == "1":
        print("\nДодаємо автозапуск...")
        if setup_autostart():
            print("✅ Автозапуск успішно налаштовано!")
            print("ATLAS буде запускатися разом з Windows.")
        else:
            print("❌ Помилка налаштування автозапуску.")
    elif choice == "2":
        print("\nВидаляємо автозапуск...")
        if remove_autostart():
            print("✅ Автозапуск успішно видалено!")
        else:
            print("❌ Помилка видалення автозапуску.")
    else:
        print("❌ Невірний вибір.")
