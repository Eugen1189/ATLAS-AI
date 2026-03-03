import os
import requests
import time
import threading
from dotenv import load_dotenv
from core.i18n import lang

# Global dictionary to store pending confirmations
# Key: message_id, Value: {"event": threading.Event(), "result": None}
PENDING_CONFIRMATIONS = {}

def _poll_telegram(axis_core):
    """Background polling process for Telegram messages and callbacks."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
    load_dotenv(dotenv_path=env_path)
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print(lang.get("telegram.keys_not_found"))
        return

    print(lang.get("telegram.starting_listen"))
    offset = 0
    send_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
            params = {"offset": offset, "timeout": 30}
            response = requests.get(url, params=params, timeout=40).json()
            
            if response.get("ok"):
                for update in response["result"]:
                    offset = update["update_id"] + 1
                    
                    # Process callback_query (button clicks)
                    if "callback_query" in update:
                        cb_query = update["callback_query"]
                        cb_data = cb_query.get("data")
                        cb_msg = cb_query.get("message")
                        
                        if cb_msg and str(cb_msg.get("chat", {}).get("id")) == str(chat_id):
                            msg_id = cb_msg.get("message_id")
                            print(lang.get("telegram.incoming_btn", btn=cb_data))
                            
                            # Answer Telegram that we received the click (so the button doesn't 'hang')
                            cb_id = cb_query.get("id")
                            requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": cb_id})
                            
                            if msg_id in PENDING_CONFIRMATIONS:
                                if cb_data == "confirm_yes":
                                    PENDING_CONFIRMATIONS[msg_id]["result"] = True
                                    new_text = f"{cb_msg.get('text')}\n\n" + lang.get("telegram.confirm_yes_text")
                                elif cb_data == "confirm_no":
                                    PENDING_CONFIRMATIONS[msg_id]["result"] = False
                                    new_text = f"{cb_msg.get('text')}\n\n" + lang.get("telegram.confirm_no_text")
                                
                                # Remove buttons and update text
                                requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                                    "chat_id": chat_id,
                                    "message_id": msg_id,
                                    "text": new_text,
                                    "reply_markup": {"inline_keyboard": []},
                                    "parse_mode": "HTML"
                                })
                                
                                # Notify the thread waiting for the answer
                                PENDING_CONFIRMATIONS[msg_id]["event"].set()
                            continue
                            
                    message = update.get("message", {})
                    
                    if str(message.get("chat", {}).get("id")) == str(chat_id):
                        text = message.get("text")
                        voice = message.get("voice")
                        
                        # Process voice messages
                        if voice:
                            print(lang.get("telegram.incoming_voice"))
                            requests.post(send_url, json={
                                "chat_id": chat_id, 
                                "text": lang.get("telegram.voice_response")
                            })
                            print(lang.get("system.prompt"), end="", flush=True)
                            continue
                            
                        # Process text messages
                        if text:
                            print(lang.get("telegram.incoming_text", text=text))
                            
                            try:
                                context_prompt = f"(Telegram message): {text}"
                                reply = axis_core.think(context_prompt)
                                
                                print(lang.get("telegram.outgoing_reply"))
                                requests.post(send_url, json={"chat_id": chat_id, "text": reply, "parse_mode": "HTML"})
                            
                            except Exception as core_error:
                                # NOW WE CAN SEE LIMIT ERRORS!
                                error_str = str(core_error)
                                print(lang.get("telegram.core_error", error=error_str))
                                
                                if "429" in error_str or "Quota" in error_str:
                                    msg = lang.get("telegram.quota_error")
                                else:
                                    msg = lang.get("telegram.sys_error", error=error_str[:50])
                                    
                                requests.post(send_url, json={"chat_id": chat_id, "text": msg})
                                
                            print(lang.get("system.prompt"), end="", flush=True)
                            
        except requests.exceptions.RequestException:
            time.sleep(5) # Ignore internet connection drops
        except Exception as e:
            print(lang.get("telegram.crit_error", error=e))
            time.sleep(5)
        
        time.sleep(1)

def start_telegram_listener(axis_core):
    """Starts the Telegram listener in a background daemon thread."""
    thread = threading.Thread(target=_poll_telegram, args=(axis_core,), daemon=True)
    thread.start()