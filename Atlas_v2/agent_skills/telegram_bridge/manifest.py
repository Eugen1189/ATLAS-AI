import os
import requests
from dotenv import load_dotenv

# Динамічно знаходимо шлях до .env
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

def send_telegram_message(text: str) -> str:
    """
    Відправляє текстове повідомлення користувачу прямо на його смартфон у Telegram.
    Використовуй цей інструмент, коли:
    1. Користувач прямо просить "скинь мені це в телеграм", "відправ на телефон".
    2. Тобі потрібно передати йому довгий звіт, код або посилання, яке зручно читати з телефону.
    3. Ти закінчив виконання довгої фонової задачі і хочеш сповістити користувача.
    
    Args:
        text: Текст повідомлення, яке потрібно відправити.
    """
    print(f"📱 [Telegram Bridge]: Відправляю повідомлення на смартфон...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return "Помилка: TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID не налаштовані в .env файлі."
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML" # Дозволяє Атласу використовувати базове форматування (жирний, курсив)
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return "Повідомлення успішно доставлено на смартфон користувача."
        else:
            return f"Помилка API Telegram: {response.text}"
    except Exception as e:
        return f"Помилка з'єднання з Telegram: {e}"

def send_telegram_file(file_path: str, caption: str = "") -> str:
    """
    Відправляє файл (фото, документ) у Telegram.
    Використовуй цей інструмент, коли користувач просить надіслати скріншот або звіт.
    """
    print(f"📱 [Telegram Bridge]: Відправляю файл {file_path}...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return "Помилка: TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID не налаштовані в .env файлі."
        
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')):
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        
    try:
        with open(file_path, 'rb') as f:
            if 'sendPhoto' in url:
                files = {'photo': f}
            else:
                files = {'document': f}
            
            data = {'chat_id': chat_id}
            if caption:
                data['caption'] = caption
                
            response = requests.post(url, data=data, files=files, timeout=30)
            
            if response.status_code == 200:
                return f"✅ Файл {file_path} надіслано успішно."
            else:
                return f"Помилка API Telegram: {response.text}"
    except Exception as e:
        return f"Помилка відправки файлу: {e}"

# Експортуємо інструменти для Оркестратора
EXPORTED_TOOLS = [send_telegram_message, send_telegram_file]