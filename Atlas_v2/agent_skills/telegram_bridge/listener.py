import os
import requests
import time
import threading
import json
import re
from .utils import format_telegram_response
from core.logger import logger
from core.i18n import lang
from core.system.path_utils import load_environment

PENDING_CONFIRMATIONS = {}


def _poll_telegram(axis_core):
    """Refined 2026 Background Poller: Secure, fast, and light (v3.6.8)."""
    load_environment()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    # Security: Multi-user whitelist support
    raw_allowed = os.getenv("TELEGRAM_ALLOWED_IDS", chat_id or "")
    allowed_ids = {uid.strip() for uid in str(raw_allowed).split(",") if uid.strip()}
    
    if not token or not chat_id:
        logger.error("telegram.keys_not_found")
        return

    logger.info("telegram.starting_listen", chat_id=chat_id)
    offset = 0
    poll_url = f"https://api.telegram.org/bot{token}/getUpdates"
    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
    
    while True:
        try:
            # Long-polling for efficiency
            response = requests.get(poll_url, params={"offset": offset, "timeout": 30}, timeout=40).json()
            
            if response.get("ok"):
                for update in response.get("result", []):
                    offset = update["update_id"] + 1
                    
                    # 1. Process Buttons (Confirmation Protocol)
                    if "callback_query" in update:
                        cq = update["callback_query"]
                        cq_id = cq.get("id")
                        msg = cq.get("message", {})
                        data = cq.get("data")
                        
                        # Verify chat security
                        if str(msg.get("chat", {}).get("id")) != str(chat_id): continue
                        
                        # Answer Telegram
                        requests.post(f"https://api.telegram.org/bot{token}/answerCallbackQuery", json={"callback_query_id": cq_id})
                        
                        msg_id = msg.get("message_id")
                        if msg_id in PENDING_CONFIRMATIONS:
                            res = (data == "confirm_yes")
                            PENDING_CONFIRMATIONS[msg_id]["result"] = res
                            
                            icon = "✅" if res else "❌"
                            label = lang.get("telegram.confirm_yes_text" if res else "telegram.confirm_no_text")
                            new_text = f"{msg.get('text')}\n\n{icon} {label}"
                            
                            # Clean UI buttons
                            requests.post(f"https://api.telegram.org/bot{token}/editMessageText", json={
                                "chat_id": chat_id,
                                "message_id": msg_id,
                                "text": new_text,
                                "reply_markup": {"inline_keyboard": []},
                                "parse_mode": "HTML"
                            })
                            
                            PENDING_CONFIRMATIONS[msg_id]["event"].set()
                        continue
                        
                    # 2. Process Messages
                    msg = update.get("message", {})
                    sender_id = str(msg.get("from", {}).get("id", ""))
                    msg_chat_id = str(msg.get("chat", {}).get("id", ""))
                    
                    # Security Guard: Only Main Chat or Whitelisted IDs
                    if msg_chat_id != str(chat_id) and sender_id not in allowed_ids:
                        logger.warning("telegram.unauthorized_access", sender=sender_id)
                        continue
                    
                    text = msg.get("text", "").strip()
                    
                    if not text: continue
                    
                    # --- INTERNAL COMMANDS (Fast Track) ---
                    if text.lower() == "/status":
                        from core.system.discovery import EnvironmentDiscoverer
                        disc = EnvironmentDiscoverer()
                        finds = disc.run_full_discovery(store_in_memory=False)
                        
                        skills = ", ".join(list(axis_core.tool_index.keys()))
                        count = len(axis_core.available_tools)
                        hw = finds.get("hardware", {})
                        
                        report = (
                            f"📡 <b>AXIS CORE STATUS</b> (v3.6.8)\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"🛡️ <b>Security:</b> BUNKER v5.5 (ACTIVE)\n"
                            f"🔧 <b>Skills:</b> {count} tools in {len(axis_core.tool_index)} modules.\n"
                            f"📦 <b>Categories:</b> {skills}\n"
                            f"💻 <b>System:</b> {hw.get('cpu_count')} Cores | {hw.get('ram_gb', '8')}GB RAM\n"
                            f"🚀 <b>Workspace:</b> <code>{os.path.basename(axis_core.project_root)}</code>\n"
                            f"━━━━━━━━━━━━━━━━━━━━\n"
                            f"<i>Command status: READY</i>"
                        )
                        requests.post(send_url, json={"chat_id": chat_id, "text": report, "parse_mode": "HTML"})
                        continue
                        
                    if text.lower() == "/hot_reload_skills":
                        res = axis_core.hot_reload_skills()
                        requests.post(send_url, json={"chat_id": chat_id, "text": f"🔄 <b>RELOAD:</b> {res}", "parse_mode": "HTML"})
                        continue

                    # --- CORE PROCESSING ---
                    logger.info("telegram.incoming", text=text[:50])
                    
                    try:
                        # Direct conscious input into the core
                        raw_reply = axis_core.think(text, source=f"telegram:{sender_id}")
                        reply = format_telegram_response(raw_reply)
                        
                        if reply:
                            requests.post(send_url, json={
                                "chat_id": chat_id, 
                                "text": reply, 
                                "parse_mode": "Markdown"
                            })
                    except Exception as e:
                        logger.error("telegram.think_failed", error=str(e))
                        requests.post(send_url, json={"chat_id": chat_id, "text": f"⚠️ <b>Internal Error:</b> {str(e)[:100]}", "parse_mode": "HTML"})

        except requests.RequestException:
            time.sleep(5)
        except Exception as e:
            logger.critical("telegram.critical_failure", error=str(e))
            time.sleep(5)
            
        time.sleep(1)

def start_telegram_listener(axis_core):
    """Starts the modernized 2026 Telegram Bridge in a background thread."""
    thread = threading.Thread(target=_poll_telegram, args=(axis_core,), daemon=True)
    thread.start()
    logger.info("system.telegram_bridge_active")