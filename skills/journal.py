import os
import datetime
import threading
import json
import glob
from pathlib import Path
from dotenv import load_dotenv
import google.generativeai as genai

# Завантаження ключів
current_dir = Path(__file__).resolve().parent.parent
env_path = current_dir / '.env'
load_dotenv(dotenv_path=env_path)

# Додаємо батьківську директорію для імпорту config
import sys
sys.path.insert(0, str(current_dir))

import config

class Journal:
    def __init__(self):
        import config
        self.memories_dir = str(config.MEMORIES_DIR)
        if not os.path.exists(self.memories_dir):
            os.makedirs(self.memories_dir)

        # Завантаження API ключа з config.py
        api_key = config.GOOGLE_API_KEY
        if api_key:
            genai.configure(api_key=api_key)
            try:
                # Використовуємо моделі з config
                self.model = genai.GenerativeModel(config.GEMINI_DEFAULT_MODEL)
                print(f"[ЖУРНАЛ] Model: {config.GEMINI_DEFAULT_MODEL}")
            except:
                try:
                    self.model = genai.GenerativeModel(config.GEMINI_FALLBACK_MODEL)
                    print(f"[ЖУРНАЛ] Model: {config.GEMINI_FALLBACK_MODEL} (Fallback)")
                except Exception as e:
                    print(f"[ЖУРНАЛ] Помилка ініціалізації моделі: {e}")
                    self.model = None
        else:
            print("⚠️ [ЖУРНАЛ] Немає API ключа!")
            self.model = None

    def _save_entry(self, folder_name, topic_name, text):
        """
        Створює файл у динамічній папці.
        Приклад: memories/Nauka/Fizyka__2026-01-08_15-00.txt
        """
        # 1. Чистимо імена від сміття (пробіли на підкреслення)
        clean_folder = folder_name.strip().replace(" ", "_").replace("/", "-")
        clean_topic = topic_name.strip().replace(" ", "_").replace("/", "-")
        
        # 2. Створюємо шлях до папки
        folder_path = os.path.join(self.memories_dir, clean_folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"📂 [ЖУРНАЛ] Створено нову папку: {clean_folder}")
        
        # 3. Генеруємо ім'я файлу (Тема + Час для унікальності)
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{clean_topic}__{timestamp}.txt"
        full_path = os.path.join(folder_path, filename)
        
        # 4. Записуємо
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(text)
            print(f"💾 [ЖУРНАЛ] Збережено: {clean_folder}/{filename}")
        except Exception as e:
            print(f"❌ Помилка запису: {e}")

    def read_category(self, category_name, limit=5):
        """
        Читає файли з конкретної папки (якщо вона існує).
        """
        target_dir = os.path.join(self.memories_dir, category_name)
        if not os.path.exists(target_dir):
            return None

        files = glob.glob(os.path.join(target_dir, "*.txt"))
        if not files: 
            return None

        files.sort(key=os.path.getmtime)
        recent_files = files[-limit:]
        
        content = ""
        for p in recent_files:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    content += f"--- {os.path.basename(p)} ---\n{f.read()}\n"
            except: 
                pass
        return content

    def analyze_and_save(self, user_text, ai_response):
        """
        AI аналізує діалог і сам вирішує, яку папку створити і як назвати файл.
        """
        def background_task():
            if not self.model:
                return
                
            # Ігноруємо надто короткі діалоги
            if len(user_text) < 5 and len(ai_response) < 10: 
                return

            prompt = f"""
            Проаналізуй діалог і класифікуй його для архіву.

            User: "{user_text}"
            AI: "{ai_response}"

            Твоє завдання - створити JSON з трьома полями:

            1. "folder": Назва папки (Одним словом, Англійською або Транслітом). 
               Приклади: Science, Nauka, Coding, Personal, History.

            2. "filename": Назва файлу (Коротко суть, 2-3 слова, Англійською або Транслітом).
               Приклади: Quantum_Physics, React_Bug, Mom_Birthday.

            3. "entry": Короткий зміст або сам текст (суть).

            Якщо це просто балачки ("привіт", "як справи") -> поверни {{"folder": "SKIP"}}
            
            Формат відповіді (JSON):
            {{ "folder": "Nauka", "filename": "Fizyka", "entry": "Текст статті..." }}
            """

            try:
                res = self.model.generate_content(prompt)
                clean_json = res.text.strip().replace("```json", "").replace("```", "")
                data = json.loads(clean_json)
                
                folder = data.get("folder", "SKIP")
                filename = data.get("filename", "Note")
                entry = data.get("entry", "")
                
                if folder != "SKIP" and entry:
                    self._save_entry(folder, filename, entry)
                    
            except Exception as e:
                print(f"⚠️ [ЖУРНАЛ] Помилка: {e}")

        threading.Thread(target=background_task, daemon=True).start()
    
    def save_direct(self, folder_name, topic_name, full_text):
        """
        🔥 ПРЯМИЙ ЗАПИС: Зберігає текст як є, без скорочень.
        
        Використовується для збереження повних текстів (статті, реферати, тощо)
        без аналізу AI та без обмежень на довжину.
        
        Args:
            folder_name: Назва папки (наприклад, "Creation")
            topic_name: Назва файлу (наприклад, "Article_Odin")
            full_text: Повний текст для збереження
        """
        # 1. Чистимо імена
        clean_folder = folder_name.strip().replace(" ", "_").replace("/", "-")
        clean_topic = topic_name.strip().replace(" ", "_").replace("/", "-")[:50]  # Обрізаємо, щоб не було надто довгим
        
        # 2. Шлях
        folder_path = os.path.join(self.memories_dir, clean_folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
            print(f"📂 [ЖУРНАЛ] Створено нову папку: {clean_folder}")
        
        # 3. Ім'я файлу з часом
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"{clean_topic}__{timestamp}.txt"
        full_path = os.path.join(folder_path, filename)
        
        # 4. Запис
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(full_text)
            print(f"💾 [ЖУРНАЛ] Збережено ПОВНИЙ документ: {clean_folder}/{filename}")
        except Exception as e:
            print(f"❌ Помилка прямого запису: {e}")
