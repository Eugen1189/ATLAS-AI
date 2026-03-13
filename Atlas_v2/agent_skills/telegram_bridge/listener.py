import os
import requests
import time
import threading
from dotenv import load_dotenv
from core.i18n import lang

# Global dictionary to store pending confirmations
# Key: message_id, Value: {"event": threading.Event(), "result": None}
PENDING_CONFIRMATIONS = {}

def _format_response(raw_result) -> str:
    """Filters out technical JSON data, returning only the user-facing response (v2.9.7)."""
    if isinstance(raw_result, dict):
        return raw_result.get("response", str(raw_result))
    
    text = str(raw_result).strip()
    
    # If the response is pure JSON tool call (due to Strict Mode)
    if text.startswith('{') and '"tool_name"' in text:
        try:
            import json
            data = json.loads(text)
            return f"[AXIS]: Виконую {data.get('tool_name')}..."
        except: pass
        
    return text

def _poll_telegram(axis_core):
    """Background polling process for Telegram messages and callbacks."""
    from core.system.path_utils import load_environment
    load_environment()

    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Whitelist: comma-separated allowed user IDs. Falls back to the main chat_id if not set.
    raw_allowed = os.getenv("TELEGRAM_ALLOWED_IDS", chat_id or "")
    allowed_ids = {uid.strip() for uid in raw_allowed.split(",") if uid.strip()}
    
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
                    sender_id = str(message.get("from", {}).get("id", ""))
                    
                    # --- Whitelist Check ---
                    if sender_id and allowed_ids and sender_id not in allowed_ids:
                        from core.logger import logger
                        logger.warning("telegram.unauthorized_user", sender_id=sender_id)
                        # Silently ignore unauthorized senders (don't reveal the bot exists)
                        continue
                    
                    if str(message.get("chat", {}).get("id")) == str(chat_id):
                        text = message.get("text")
                        voice = message.get("voice")
                        
                        # Process voice messages (v2.9.6 - Voice Bridge)
                        if voice:
                            print(lang.get("telegram.incoming_voice"))
                            file_id = voice.get("file_id")
                            
                            # 1. Get file path from Telegram
                            file_info = requests.get(f"https://api.telegram.org/bot{bot_token}/getFile", 
                                                    params={"file_id": file_id}).json()
                            if file_info.get("ok"):
                                file_path = file_info["result"]["file_path"]
                                download_url = f"https://api.telegram.org/file/bot{bot_token}/{file_path}"
                                
                                # 2. Download OGG to temp file
                                import tempfile
                                temp_ogg = os.path.join(tempfile.gettempdir(), f"tg_voice_{update['update_id']}.ogg")
                                with open(temp_ogg, 'wb') as f:
                                    f.write(requests.get(download_url).content)
                                    
                                # 3. Transcribe via audio_interface
                                from agent_skills.audio_interface.manifest import transcribe_audio_file

                                text = transcribe_audio_file(temp_ogg)
                                
                                # Cleanup OGG
                                if os.path.exists(temp_ogg): os.remove(temp_ogg)
                                
                                if text:
                                    print(f"[TG VOICE]: {text}")
                                    tg_source = f"telegram:{sender_id or chat_id}"
                                    raw_reply = axis_core.think(f"(Voice Msg): {text}", source=tg_source)
                                    reply = _format_response(raw_reply)
                                    
                                    # 4. Respond with Text (Silent Mode v2.9.7)
                                    res = requests.post(send_url, json={
                                        "chat_id": chat_id, 
                                        "text": reply, 
                                        "parse_mode": "HTML"
                                    })
                                    if res.status_code != 200:
                                        print(f"[TG ERROR]: {res.text}")
                                else:
                                    requests.post(send_url, json={"chat_id": chat_id, "text": "Не вдалося розпізнати звук."})
                            
                            continue
                            
                        # Process text messages
                        if text:
                            print(lang.get("telegram.incoming_text", text=text))
                            
                            # --- Internal Command: /status ---
                            if text.strip().lower() == "/status":
                                from core.system.discovery import EnvironmentDiscoverer
                                f = EnvironmentDiscoverer.findings
                                hw = f.get("hardware", {})
                                ides = list(f.get("ides", {}).keys()) or ["None found"]
                                tools = [t for t in f.get("tools", {})]
                                
                                report = (
                                    f"*🖥 AXIS CORE STATUS*\n"
                                    f"──────────────\n"
                                    f"*🏠 IDEs:* {', '.join(ides)}\n"
                                    f"*⚙️ Hardware:* {hw.get('ram_gb')}GB RAM | {hw.get('gpu')}\n"
                                    f"*🛠 Tools:* {', '.join(tools[:5])}...\n"
                                    f"*📁 Workspace:* {f.get('workspaces')[0] if f.get('workspaces') else 'Not mapped'}\n"
                                    f"──────────────\n"
                                    f"_Ready for Remote Command._"
                                )
                                requests.post(send_url, json={"chat_id": chat_id, "text": report, "parse_mode": "Markdown"})
                                continue

                            try:
                                # Tag source with sender's Telegram ID for per-user rate limiting
                                tg_source = f"telegram:{sender_id or chat_id}"
                                context_prompt = f"(Telegram message): {text}"
                                raw_reply = axis_core.think(context_prompt, source=tg_source)
                                reply = _format_response(raw_reply)
                                
                                print(lang.get("telegram.outgoing_reply"))
                                requests.post(send_url, json={
                                    "chat_id": chat_id, 
                                    "text": reply, 
                                    "parse_mode": "Markdown"
                                })
                            
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