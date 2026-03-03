import os
import requests
import threading
from dotenv import load_dotenv
from core.i18n import lang

# Import dictionary to store confirmation states
from .listener import PENDING_CONFIRMATIONS

# Dynamically find the path to .env (C:\Projects\Atlas\.env)
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

def send_telegram_message(text: str) -> str:
    """
    Sends a text message to the user directly to their smartphone on Telegram.
    Use this tool when:
    1. The user explicitly asks to "send this to telegram", "send to phone".
    2. You need to send a long report, code, or link that is convenient to read on a phone.
    3. You have finished a long background task and want to notify the user.
    
    Args:
        text: Message text to send.
    """
    print(lang.get("telegram.sending_msg"))
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return lang.get("telegram.env_error")
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML" # Allows Atlas to use basic formatting (bold, italic)
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            return lang.get("telegram.msg_delivered")
        else:
            return lang.get("telegram.api_error", error=response.text)
    except Exception as e:
        return lang.get("telegram.conn_error", error=e)

def send_telegram_file(file_path: str, caption: str = "") -> str:
    """
    Sends a file (photo, document) to Telegram.
    Use this tool when the user asks you to send a screenshot or report.
    """
    print(lang.get("telegram.sending_file", path=file_path))
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        return lang.get("telegram.env_error")
        
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
                print(f"[Telegram Bridge]: {lang.get('telegram.file_sent', path=file_path)}")
                return lang.get("telegram.file_sent", path=file_path)
            else:
                print(lang.get("telegram.server_error", code=response.status_code, text=response.text))
                return lang.get("telegram.api_error", error=response.text)
    except Exception as e:
        print(f"[Telegram Bridge]: Critical Error: {e}")
        return lang.get("telegram.file_send_error", error=e)

def ask_user_confirmation(prompt: str) -> bool:
    """
    Asks the user to confirm a specific action via Telegram (Human-in-the-loop).
    Use this tool BEFORE:
    - Deleting or significantly overwriting important files.
    - Executing git push or similar actions that affect external systems (deploy, etc.).
    - Running commands that could potentially harm the system (rm -rf, formatting, etc.).
    
    The tool will pause your execution and wait until the user clicks
    the "Confirm" or "Decline" button in Telegram.
    
    Args:
        prompt: A clear explanation of what exactly you are about to do. Example: "I am ready to git push. Confirm?"
    
    Returns:
        True if the user confirmed the action (you can proceed).
        False if the user declined the action (must be cancelled). Always inform the user if you cancel something.
    """
    print(lang.get("telegram.req_confirm", prompt=prompt))
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("[Telegram Bridge]: " + lang.get("telegram.env_error"))
        return False
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"{lang.get('telegram.confirm_title')}\n\n{prompt}",
        "parse_mode": "HTML",
        "reply_markup": {
            "inline_keyboard": [
                [
                    {"text": lang.get("telegram.confirm_yes"), "callback_data": "confirm_yes"},
                    {"text": lang.get("telegram.confirm_no"), "callback_data": "confirm_no"}
                ]
            ]
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            msg_id = response.json().get("result", {}).get("message_id")
            if msg_id:
                # Create an event to wait on
                evt = threading.Event()
                PENDING_CONFIRMATIONS[msg_id] = {"event": evt, "result": None}
                
                print(lang.get("telegram.waiting_resp", id=msg_id))
                # Block tool execution, wait for 5 minutes (300 seconds)
                confirmed = evt.wait(timeout=300.0) 
                
                if confirmed:
                    result = PENDING_CONFIRMATIONS[msg_id]["result"]
                    print(lang.get("telegram.user_replied_yes") if result else lang.get("telegram.user_replied_no"))
                    del PENDING_CONFIRMATIONS[msg_id]
                    return bool(result)
                else:
                    print(lang.get("telegram.timeout"))
                    # Update message to remove buttons since time expired
                    title = lang.get("telegram.confirm_title")
                    timeout_msg = lang.get("telegram.timeout_msg")
                    requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": msg_id,
                        "text": f"{title}\n\n{prompt}{timeout_msg}",
                        "reply_markup": {"inline_keyboard": []},
                        "parse_mode": "HTML"
                    })
                    if msg_id in PENDING_CONFIRMATIONS:
                        del PENDING_CONFIRMATIONS[msg_id]
                    return False
            else:
                print(lang.get("telegram.no_msg_id"))
                return False
        else:
            print(lang.get("telegram.api_error", error=response.text))
            return False
    except Exception as e:
        print(lang.get("telegram.conn_error", error=e))
        return False

# Export tools for Orchestrator
EXPORTED_TOOLS = [send_telegram_message, send_telegram_file, ask_user_confirmation]