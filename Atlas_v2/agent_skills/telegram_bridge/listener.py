import os
import requests
import time
import threading
from dotenv import load_dotenv

# Глобальний словник для зберігання очікуваних підтверджень
# Ключ: message_id, Значення: {"event": threading.Event(), "result": None}
PENDING_CONFIRMATIONS = {}

def _poll_telegram(atlas_core):
    """Фоновий процес для Telegram"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
    load_dotenv(dotenv_path=env_path)
    
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("⚠️ [Telegram Listener]: Ключі не знайдено.")
        return

    print("📡 [Telegram Listener]: Починаю прослуховування вхідних повідомлень...")
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
                    
                    # Обробка callback_query (натискання кнопок)
                    if "callback_query" in update:
                        cb_query = update["callback_query"]
                        cb_data = cb_query.get("data")
                        cb_msg = cb_query.get("message")
                        
                        if cb_msg and str(cb_msg.get("chat", {}).get("id")) == str(chat_id):
                            msg_id = cb_msg.get("message_id")
                            print(f"\n📱 [Telegram Вхідне]: Натиснуто кнопку: {cb_data}")
                            
                            # Відповідаємо Telegram, що ми прийняли натискання (щоб кнопка не 'висіла')
                            cb_id = cb_query.get("id")
                            requests.post(f"https://api.telegram.org/bot{bot_token}/answerCallbackQuery", json={"callback_query_id": cb_id})
                            
                            if msg_id in PENDING_CONFIRMATIONS:
                                if cb_data == "confirm_yes":
                                    PENDING_CONFIRMATIONS[msg_id]["result"] = True
                                    new_text = f"{cb_msg.get('text')}\n\n✅ <b>Підтверджено</b>"
                                elif cb_data == "confirm_no":
                                    PENDING_CONFIRMATIONS[msg_id]["result"] = False
                                    new_text = f"{cb_msg.get('text')}\n\n❌ <b>Відхилено</b>"
                                
                                # Забираємо кнопки і оновлюємо текст
                                requests.post(f"https://api.telegram.org/bot{bot_token}/editMessageText", json={
                                    "chat_id": chat_id,
                                    "message_id": msg_id,
                                    "text": new_text,
                                    "reply_markup": {"inline_keyboard": []},
                                    "parse_mode": "HTML"
                                })
                                
                                # Сповіщаємо потік, що чекає на відповідь
                                PENDING_CONFIRMATIONS[msg_id]["event"].set()
                            continue
                            
                    message = update.get("message", {})
                    
                    if str(message.get("chat", {}).get("id")) == str(chat_id):
                        text = message.get("text")
                        voice = message.get("voice")
                        
                        # Обробка голосових повідомлень
                        if voice:
                            print(f"\n📱 [Telegram Вхідне]: 🎤 Голосове повідомлення (поки не підтримується)")
                            requests.post(send_url, json={
                                "chat_id": chat_id, 
                                "text": "🤖 Прийняв голосове повідомлення! Але поки мій аудіо-модуль для Telegram монтується, будь ласка, напиши текстом."
                            })
                            print("\n👤 Ви (текст або ENTER для мікрофона): ", end="", flush=True)
                            continue
                            
                        # Обробка текстових повідомлень
                        if text:
                            print(f"\n📱 [Telegram Вхідне]: {text}")
                            
                            try:
                                context_prompt = f"(Повідомлення з Telegram): {text}"
                                reply = atlas_core.think(context_prompt)
                                
                                print(f"🤖 [Telegram Вихідне]: Відправляю відповідь на телефон...")
                                requests.post(send_url, json={"chat_id": chat_id, "text": reply, "parse_mode": "HTML"})
                            
                            except Exception as core_error:
                                # ТЕПЕР МИ БАЧИМО ПОМИЛКУ ЛІМІТІВ!
                                error_str = str(core_error)
                                print(f"\n❌ [Telegram Помилка Ядра]: {error_str}")
                                
                                if "429" in error_str or "Quota" in error_str:
                                    msg = "⚠️ Вибач, Євгене. Google тимчасово заблокував мої API-квоти. Чекаю на оновлення лімітів."
                                else:
                                    msg = f"⚠️ Системна помилка Ядра: {error_str[:50]}..."
                                    
                                requests.post(send_url, json={"chat_id": chat_id, "text": msg})
                                
                            print("\n👤 Ви (текст або ENTER для мікрофона): ", end="", flush=True)
                            
        except requests.exceptions.RequestException:
            time.sleep(5) # Ігноруємо обриви інтернету
        except Exception as e:
            print(f"\n❌ [Telegram Критична Помилка]: {e}")
            time.sleep(5)
        
        time.sleep(1)

def start_telegram_listener(atlas_core):
    thread = threading.Thread(target=_poll_telegram, args=(atlas_core,), daemon=True)
    thread.start()