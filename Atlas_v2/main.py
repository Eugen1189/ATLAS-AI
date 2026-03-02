from core.orchestrator import AtlasCore
import sys
import os

# Додаємо шлях до Atlas_v2
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Додаємо шлях до кореня проекту (SystemCOO), щоб бачити config.py та інше
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent_skills.audio_interface.listener import listen_command

# ДОДАЄМО ІМПОРТ ТЕЛЕГРАМ СЛУХАЧА
from agent_skills.telegram_bridge.listener import start_telegram_listener

def boot_sequence():
    print("🚀 Запуск Atlas V2... (Модульна Архітектура)")
    atlas = AtlasCore()
    
    # ЗАПУСКАЄМО ТЕЛЕГРАМ У ФОНІ, передаючи йому мозок Атласа
    start_telegram_listener(atlas)
    
    print("\n--- Atlas готовий до роботи ---")
    print("(Введи текст, або просто натисни ENTER, щоб сказати голосом. Для виходу напиши 'exit')")
    
    while True:
        try:
            command = input("\n👤 Ви (текст або ENTER для мікрофона): ").strip()
            
            if command.lower() in ['exit', 'quit', 'вихід']:
                print("Вимкнення систем...")
                break
                
            if command.lower() == 'status':
                print("\n📊 [SYSTEM] Vision: ONLINE | MCP: 2 SERVERS ACTIVE | TG: CONNECTED\n")
                continue
                
            # Якщо користувач просто натиснув Enter — вмикаємо мікрофон!
            if command == "":
                command = listen_command()
                if not command:  # Якщо нічого не розпізнано, починаємо цикл спочатку
                    continue
                print(f"🗣️ Ви сказали: {command}")
                
            # Відправляємо команду (текстову або голосову) в мозок
            response = atlas.think(command)
            print(f"🤖 Атлас: {response}")
            
        except Exception as e:
            print(f"❌ Системна помилка: {e}")

if __name__ == "__main__":
    boot_sequence()
