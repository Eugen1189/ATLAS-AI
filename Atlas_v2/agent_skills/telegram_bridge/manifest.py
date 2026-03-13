import os
import json
import requests
import threading
import re
from .listener import PENDING_CONFIRMATIONS
from core.skills.wrapper import agent_tool

def clean_llm_text(text: str) -> str:
    """Вирізає галюцинації JSON з фінального тексту"""
    # Якщо текст виглядає як маркдаун JSON блок
    if "```json" in text:
        # Спробуємо витягти значення "response", якщо воно є
        try:
            match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
            if match:
                json_str = match.group(1)
                data = json.loads(json_str)
                if "response" in data:
                    return data["response"]
        except Exception:
            pass
        # Якщо не вийшло розпарсити, просто вирізаємо маркдаун
        text = text.replace("```json", "").replace("```", "").strip()
    return text

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
    
    # Санітарія тексту перед відправкою
    clean_text = clean_llm_text(text)
    
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{t}/sendMessage", 
            json={"chat_id": c, "text": clean_text, "parse_mode": "HTML"}, 
            timeout=10
        )
        if r.status_code == 200:
            return f"✅ Повідомлення успішно відправлено в Telegram: '{text[:50]}...'"
        return f"❌ Помилка Telegram API: {r.text}"
    except Exception as e: 
        return f"❌ Критична помилка з'єднання з Telegram: {e}"

@agent_tool
def send_telegram_photo(path: str, text: str = "", **kwargs) -> str:
    """Відправляє фото, скріншот або файл з комп'ютера на телефон Командора."""
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not t or not c: 
        return "❌ Помилка: Telegram налаштування відсутні."
        
    path = _resolve_path(path)
    if not os.path.exists(path):
        return f"❌ Помилка: Файл за шляхом {path} не знайдено."

    url_photo = f"https://api.telegram.org/bot{t}/sendPhoto"
    url_doc = f"https://api.telegram.org/bot{t}/sendDocument"

    try:
        with open(path, 'rb') as f:
            if path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                # 1. Пробуємо відправити як фото
                r = requests.post(url_photo, data={'chat_id': c, 'caption': text}, files={'photo': f}, timeout=30)
                resp_data = r.json()
                
                # 2. Якщо Telegram свариться на розміри (Error 400 DIMENSIONS)
                if not resp_data.get("ok") and "DIMENSIONS" in resp_data.get("description", "").upper():
                    f.seek(0) # Повертаємо курсор файлу на початок
                    # Відправляємо як документ (без втрати якості і обрізання)
                    doc_r = requests.post(url_doc, data={'chat_id': c, 'caption': text}, files={'document': f}, timeout=30)
                    if doc_r.status_code == 200:
                        return f"✅ Файл {os.path.basename(path)} успішно відправлено як документ (обхід лімітів Telegram)."
                    return f"❌ Помилка Telegram API (Document fallback): {doc_r.text}"
                
                if r.status_code == 200:
                    return f"✅ Фото {os.path.basename(path)} успішно відправлено в Telegram."
                return f"❌ Помилка Telegram API: {r.text}"
            else:
                # Всі інші файли відправляємо як документ
                r = requests.post(url_doc, data={'chat_id': c, 'caption': text}, files={'document': f}, timeout=30)
                if r.status_code == 200:
                    return f"✅ Файл {os.path.basename(path)} успішно відправлено в Telegram."
                return f"❌ Помилка Telegram API: {r.text}"
    except Exception as e:
        return f"❌ Критична помилка з'єднання з Telegram під час відправки файлу: {e}"

@agent_tool
def ask_user_confirmation(text: str, **kwargs) -> bool:
    """Standard 2026 HITL: Pauses execution until user confirms action via Telegram phone app."""
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    kb = {"inline_keyboard": [[{"text": "✅ Yes", "callback_data": "confirm_yes"}, {"text": "❌ No", "callback_data": "confirm_no"}]]}
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{t}/sendMessage", 
            json={"chat_id": c, "text": f"⚠️ CONFIRMATION REQ:\n{text}", "reply_markup": kb}, 
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

@agent_tool
def send_home_report(**kwargs) -> str:
    """
    МАКРО-КОМАНДА: Робить повний звіт про стан комп'ютера (скріншот + статус заліза) 
    і негайно відправляє його в Telegram Командору.
    Використовуй це, коли користувач питає 'що вдома', 'який статус' або 'надішли скріншот і стан системи'.
    """
    from agent_skills.vision_eye.manifest import take_screenshot
    from agent_skills.diagnostics.manifest import deep_system_scan
    
    # 1. Take Screenshot
    path = take_screenshot()
    if "Failed" in path:
        return f"Error taking screenshot: {path}"

    # 2. Get System Stats
    report_text = deep_system_scan()
    caption = f"🛰️ Звіт AXIS: Система в нормі.\n{report_text}"
    
    # 3. Send to Telegram
    res = send_telegram_photo(path=path, text=caption)
    
    # 4. Vocal feedback
    try:
        from agent_skills.audio_interface.manifest import speak
        speak(text="Звіт надіслано, Командоре.")
    except Exception: pass
    
    return res

@agent_tool
def send_project_tree_visual(**kwargs) -> str:
    """
    МАКРО-КОМАНДА: Створює ВІЗУАЛЬНЕ (PNG зображення) дерево папок та файлів.
    Використовується для запитів: "візуальне дерево", "фото структури", "намалюй структуру".
    ⛔ АНТИ-ТРИГЕР: НІКОЛИ не використовуй цей інструмент, якщо користувач просить виконати стандартні консольні команди (dir, ls, tree).
    """
    import os
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return "❌ Помилка: Бібліотека Pillow не встановлена."

    report_img = "project_structure.png"
    ignore_dirs = {'.git', 'venv', '__pycache__', '.idea', 'env', '__tests__', '.pytest_cache', '.ruff_cache'}
    
    # --- КРИТИЧНИЙ ПАРАМЕТР ПРОПОРЦІЙ ---
    MAX_DEPTH = 2  # Показуватиме лише головні папки та їхній безпосередній вміст
    
    lines = []
    base_path = "."
    
    for root, dirs, files in os.walk(base_path):
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        dirs.sort()
        
        # Визначаємо рівень вкладеності
        level = 0 if root == "." else root.count(os.sep)
        
        # Обрізаємо занадто глибокі папки
        if level > MAX_DEPTH:
            del dirs[:] 
            continue
            
        indent = " " * (level * 4)
        if root != ".":
            lines.append(f"{indent}📁 {os.path.basename(root)}")
        else:
            lines.append(f"🖥️ PROJECT: {os.path.basename(os.getcwd())}")
            lines.append("-" * 50)
        
        subindent = " " * ((level + 1) * 4)
        if level < MAX_DEPTH:
            valid_files = [f for f in files if not f.endswith((".pyc", ".pyo", ".log", ".tmp")) and not f.startswith('.')]
            for f in sorted(valid_files):
                lines.append(f"{subindent}📄 {f}")

    # Запобіжник для "хвоста" списку
    if len(lines) > 60:
        lines = lines[:55] + ["", f"   ... і ще {len(lines)-55} елементів (Приховано для компактності)"]

    # --- ДИЗАЙН "ТЕРМІНАЛ Mac OS" ---
    try:
        font = ImageFont.truetype("consola.ttf", 16)
    except IOError:
        font = ImageFont.load_default()

    line_height = 24
    padding_x = 40
    padding_top = 70  # Місце під "шапку" вікна
    
    # Розрахунок пропорцій (Ширина не менше 700 пікселів для формату "екрана")
    max_chars = max((len(line) for line in lines if line), default=50)
    width = max(max_chars * 10 + padding_x * 2, 700) 
    height = len(lines) * line_height + padding_top + 30

    img = Image.new('RGB', (width, height), color=(30, 30, 34)) # Темно-сірий фон терміналу
    d = ImageDraw.Draw(img)
    
    # Малюємо кнопки вікна Mac OS (Червона, Жовта, Зелена)
    d.ellipse((20, 20, 34, 34), fill=(255, 95, 86))   
    d.ellipse((44, 20, 58, 34), fill=(255, 189, 46))  
    d.ellipse((68, 20, 82, 34), fill=(39, 201, 63))   

    y = padding_top
    for i, line in enumerate(lines):
        # Кольорова схема IDE
        if i == 0: color = (152, 195, 121)       # Зелений корінь
        elif "📁" in line: color = (97, 175, 239) # Блакитні папки
        elif "🖥️" in line: color = (255, 255, 255)# Білий заголовок
        else: color = (171, 178, 191)            # Світло-сірий текст
        
        d.text((padding_x, y), line, fill=color, font=font)
        y += line_height

    img.save(report_img)
    send_telegram_photo(path=report_img, text="📸 Структура проекту (Термінальний вигляд)")
    return "SUCCESS: Зображення створено та відправлено."

EXPORTED_TOOLS = [send_telegram_message, send_telegram_photo, ask_user_confirmation, send_home_report, send_project_tree_visual]

