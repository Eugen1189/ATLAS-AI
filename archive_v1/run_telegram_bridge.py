"""
Запуск Telegram Bridge для ATLAS SystemCOO

Використання:
    1. Переконайтеся, що в config.py налаштовано:
       - TELEGRAM_BOT_TOKEN (отримайте від @BotFather)
       - ALLOWED_USER_IDS (додайте свій ID, отримайте від @userinfobot)
    
    2. Встановіть залежності:
       pip install pyTelegramBotAPI
    
    3. Запустіть bridge:
       python run_telegram_bridge.py
"""

import sys
from pathlib import Path

# Додаємо поточну директорію до шляху
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from core.atlas import AtlasCore
    from skills.telegram_bridge import TelegramBridge
    
    print("🚀 [TELEGRAM] Запуск Telegram Bridge для ATLAS...")
    
    # Ініціалізація AtlasCore
    print("🏗️ [TELEGRAM] Ініціалізація AtlasCore...")
    atlas = AtlasCore()
    atlas.start()
    print("✅ [TELEGRAM] AtlasCore запущено")
    
    # Створення та запуск Telegram Bridge
    print("🌉 [TELEGRAM] Створення Telegram Bridge...")
    bridge = TelegramBridge(atlas_core=atlas)
    
    print("\n" + "="*50)
    print("✅ Telegram Bridge готовий до роботи!")
    print("="*50 + "\n")
    
    # Запуск bridge
    bridge.start()
    
    # Чекаємо поки працює
    try:
        import time
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 [TELEGRAM] Зупинка bridge...")
        bridge.stop()
        atlas.stop()
        print("✅ [TELEGRAM] Bridge зупинено")
    
except ImportError as e:
    print(f"❌ [TELEGRAM] Помилка імпорту: {e}")
    print("\n💡 Встановіть залежності:")
    print("   pip install pyTelegramBotAPI")
    sys.exit(1)
    
except Exception as e:
    print(f"❌ [TELEGRAM] Помилка: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
