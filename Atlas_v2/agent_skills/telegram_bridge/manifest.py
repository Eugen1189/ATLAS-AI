import os
import json
import requests
import threading
from .listener import PENDING_CONFIRMATIONS
from core.skills.wrapper import agent_tool

def _resolve_path(path: str) -> str:
    """Helper to expand home and replace placeholders."""
    if not path: return path
    path = path.replace("[Your_Username]", os.getlogin())
    return os.path.abspath(os.path.expanduser(path))

@agent_tool
def send_telegram_message(text: str, **kwargs) -> str:
    """Відправляє текстове повідомлення на телефон Командора (через Telegram). Використовуй для віддалених звітів."""
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not t or not c: 
        return "❌ Помилка: Не налаштовані TELEGRAM_BOT_TOKEN або TELEGRAM_CHAT_ID у .env файлі."
    
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{t}/sendMessage", 
            json={"chat_id": c, "text": text, "parse_mode": "HTML"}, 
            timeout=10
        )
        if r.status_code == 200:
            return f"✅ Повідомлення успішно відправлено в Telegram: '{text[:50]}...'"
        return f"❌ Помилка Telegram API: {r.text}"
    except Exception as e: 
        return f"❌ Критична помилка з'єднання з Telegram: {e}"

@agent_tool
def send_telegram_photo(filepath: str, caption: str = "", **kwargs) -> str:
    """Відправляє фото, скріншот або файл з комп'ютера на телефон Командора."""
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not t or not c: 
        return "❌ Помилка: Telegram налаштування відсутні."
        
    path = _resolve_path(filepath)
    if not os.path.exists(path):
        return f"❌ Помилка: Файл за шляхом {path} не знайдено."

    url = f"https://api.telegram.org/bot{t}/sendDocument"
    files = {'document': open(path, 'rb')}
    
    # Визначаємо, чи це фото
    if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
        url = f"https://api.telegram.org/bot{t}/sendPhoto"
        files = {'photo': open(path, 'rb')}
    
    try:
        r = requests.post(
            url, 
            data={'chat_id': c, 'caption': caption}, 
            files=files, 
            timeout=30
        )
        if r.status_code == 200:
            return f"✅ Файл {os.path.basename(path)} успішно відправлено в Telegram."
        return f"❌ Помилка Telegram API: {r.text}"
    finally:
        # Закриваємо файл
        for f in files.values(): f.close()

@agent_tool
def ask_user_confirmation(prompt: str, **kwargs) -> bool:
    """Standard 2026 HITL: Pauses execution until user confirms action via Telegram phone app."""
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    kb = {"inline_keyboard": [[{"text": "✅ Yes", "callback_data": "confirm_yes"}, {"text": "❌ No", "callback_data": "confirm_no"}]]}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{t}/sendMessage", 
            json={"chat_id": c, "text": f"⚠️ CONFIRMATION REQ:\n{prompt}", "reply_markup": kb}, 
            timeout=10
        ).json()
        m_id = r.get("result", {}).get("message_id")
        if not m_id: return False
        
        evt = threading.Event()
        PENDING_CONFIRMATIONS[m_id] = {"event": evt, "result": None}
        
        # Чекаємо 5 хвилин
        if evt.wait(timeout=300):
            res = PENDING_CONFIRMATIONS[m_id]["result"]
            del PENDING_CONFIRMATIONS[m_id]
            return bool(res)
        return False
    except Exception: 
        return False

EXPORTED_TOOLS = [send_telegram_message, send_telegram_photo, ask_user_confirmation]

