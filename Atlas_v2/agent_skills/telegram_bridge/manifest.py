import os
import json
import requests
import threading
import re
from .listener import PENDING_CONFIRMATIONS
from core.skills.wrapper import agent_tool

def clean_llm_text(text: str) -> str:
    """Вирізає технічне сміття та теги з фінального тексту для Telegram."""
    if not text: return ""
    # Видаляємо блоки думок <thought>...</thought>
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    # Видаляємо маркдаун блоки JSON
    if "```json" in text:
        try:
            match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if match:
                data = json.loads(match.group(1))
                if "response" in data: return data["response"]
        except: pass
        text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL)
    
    return text.strip()

@agent_tool
def send_telegram_message(text: str, **kwargs) -> str:
    """Sends a text message to the Commander's phone via Telegram."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id: 
        return "❌ Error: Telegram credentials missing in .env"
    
    clean_text = clean_llm_text(text)
    if not clean_text: return "⚠️ Warning: Cleaned message text is empty."
    
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage", 
            json={"chat_id": chat_id, "text": clean_text, "parse_mode": "HTML"}, 
            timeout=10
        )
        if r.status_code == 200:
            return f"✅ Message sent to Telegram."
        return f"❌ Telegram API Error: {r.text}"
    except Exception as e: 
        return f"❌ Connection Error: {e}"

@agent_tool
def send_telegram_photo(path: str, caption: str = "", **kwargs) -> str:
    """Sends a photo, screenshot or file to the Commander's phone."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return "❌ Error: Telegram credentials missing."
    
    if not os.path.exists(path):
        return f"❌ Error: File {path} not found."

    url_photo = f"https://api.telegram.org/bot{token}/sendPhoto"
    url_doc = f"https://api.telegram.org/bot{token}/sendDocument"

    try:
        with open(path, 'rb') as f:
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                r = requests.post(url_photo, data={'chat_id': chat_id, 'caption': caption}, files={'photo': f}, timeout=30)
                if r.status_code != 200:
                    f.seek(0)
                    r = requests.post(url_doc, data={'chat_id': chat_id, 'caption': caption}, files={'document': f}, timeout=30)
            else:
                r = requests.post(url_doc, data={'chat_id': chat_id, 'caption': caption}, files={'document': f}, timeout=30)
        
        if r.status_code == 200:
            return f"✅ File {os.path.basename(path)} sent successfully."
        return f"❌ Telegram API Error: {r.text}"
    except Exception as e:
        return f"❌ Critical Connection Error: {e}"

@agent_tool
def ask_user_confirmation(text: str, **kwargs) -> bool:
    """Pauses execution and asks the Commander for confirmation via Telegram buttons."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return False
    
    keyboard = {
        "inline_keyboard": [[
            {"text": "✅ Yes", "callback_data": "confirm_yes"}, 
            {"text": "❌ No", "callback_data": "confirm_no"}
        ]]
    }
    
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage", 
            json={"chat_id": chat_id, "text": f"⚠️ <b>CONFIRMATION REQUIRED</b>\n\n{text}", "reply_markup": keyboard, "parse_mode": "HTML"}, 
            timeout=10
        ).json()
        
        msg_id = r.get("result", {}).get("message_id")
        if not msg_id: return False
        
        event = threading.Event()
        PENDING_CONFIRMATIONS[msg_id] = {"event": event, "result": None}
        
        # Wait up to 10 minutes for a response
        if event.wait(timeout=600):
            res = PENDING_CONFIRMATIONS[msg_id]["result"]
            del PENDING_CONFIRMATIONS[msg_id]
            return bool(res)
        
        # Timeout cleanup
        if msg_id in PENDING_CONFIRMATIONS: del PENDING_CONFIRMATIONS[msg_id]
        return False
    except Exception: 
        return False

EXPORTED_TOOLS = [send_telegram_message, send_telegram_photo, ask_user_confirmation]
