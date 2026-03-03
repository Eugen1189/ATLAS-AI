import os
import requests
import threading
from dotenv import load_dotenv

# Імпортуємо словник для зберігання станів підтверджень
from .listener import PENDING_CONFIRMATIONS

# Динамічно знаходимо шлях до .env (C:\Projects\Atlas\.env)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".env"))
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
    print(f"[Telegram Bridge]: Відправляю повідомлення на смартфон...")
    
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
    print(f"[Telegram Bridge]: Відправляю файл {file_path}...")
    
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
                print(f"[Telegram Bridge]: Файл {file_path} успішно надіслано.")
                return f"✅ Файл {file_path} надіслано успішно."
            else:
                print(f"[Telegram Bridge]: Помилка сервера {response.status_code}: {response.text}")
                return f"Помилка API Telegram: {response.text}"
    except Exception as e:
        print(f"[Telegram Bridge]: Критична помилка: {e}")
        return f"Помилка відправки файлу: {e}"

def ask_user_confirmation(prompt: str) -> bool:
    """
    Запитує в користувача підтвердження виконання певної дії через Telegram (Human-in-the-loop).
    Використовуй цей інструмент ПЕРЕД:
    - Видаленням або значним перезаписом важливих файлів.
    - Здійсненням git push або подібних дій, що впливають на зовнішні системи (деплой тощо).
    - Виконанням команд, які потенційно можуть пошкодити систему (rm -rf, форматування тощо).
    
    Інструмент зупинить твоє виконання і буде чекати, поки користувач натисне кнопку 
    "Підтвердити" або "Відхилити" в Telegram.
    
    Args:
        prompt: Чітке пояснення того, що саме ти збираєшся зробити. Наприклад: "Я готовий зробити git push. Підтвердити?"
    
    Returns:
        True, якщо користувач підтвердив дію (можна продовжувати).
        False, якщо користувач відхилив дію (її треба скасувати). Обов'язково повідомляй користувачу, якщо ти щось скасовуєш.
    """
    print(f"[Telegram Bridge]: Запит підтвердження: '{prompt}'...")
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("[Telegram Bridge]: Помилка - TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID не налаштовані.")
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"🛡️ <b>Запит на підтвердження</b>\n\n{prompt}",
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": "✅ Підтвердити", "callback_data": "confirm_yes"},
                    {"text": "❌ Відхилити", "callback_data": "confirm_no"}
                ]
            ]
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            msg_id = response.json().get("result", {}).get("message_id")
            if msg_id:
                # Створюємо подію для чекання
                evt = threading.Event()
                PENDING_CONFIRMATIONS[msg_id] = {"event": evt, "result": None}
                
                print(f"[Telegram Bridge]: Чекаю на відповідь користувача (повідомлення {msg_id})...")
                # Блокуємо виконання інструменту, чекаємо 5 хвилин (300 секунд)
                confirmed = evt.wait(timeout=300.0) 
                
                if confirmed:
                    result = PENDING_CONFIRMATIONS[msg_id]["result"]
                    print(f"[Telegram Bridge]: Користувач відповів: {'✅ Так' if result else '❌ Ні'}")
                    del PENDING_CONFIRMATIONS[msg_id]
                    return bool(result)
                else:
                    print(f"[Telegram Bridge]: Тайм-аут очікування відповіді (5 хв). Автоматично відхилено.")
                    # Оновлюємо повідомлення, щоб прибрати кнопки, оскільки вийшов час
                    requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "text": f"🛡️ <b>Запит на підтвердження</b>\n\n{prompt}\n\n<i>⏳ Час очікування минув.</i>",
                        "reply_markup": {"inline_keyboard": []},
                        "parse_mode": "HTML"
                    })
                    if msg_id in PENDING_CONFIRMATIONS:
                        del PENDING_CONFIRMATIONS[msg_id]
                    return False
            else:
                print("[Telegram Bridge]: Не вдалося отримати message_id від Telegram")
                return False
        else:
            print(f"[Telegram Bridge]: Помилка API Telegram: {response.text}")
            return False
    except Exception as e:
        print(f"[Telegram Bridge]: Помилка з'єднання з Telegram на стадії запиту підтвердження: {e}")
        return False

# Експортуємо інструменти для Оркестратора
EXPORTED_TOOLS = [send_telegram_message, send_telegram_file, ask_user_confirmation]