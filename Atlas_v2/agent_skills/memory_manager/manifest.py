import sqlite3
import os
from datetime import datetime

# Визначаємо шлях до бази даних у папці memories
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "memories"))
os.makedirs(db_dir, exist_ok=True)
DB_PATH = os.path.join(db_dir, "atlas_memory.db")

# Автоматичне створення таблиці при першому запуску
def _init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT,
            fact TEXT,
            timestamp TEXT
        )
    ''')
    conn.commit()
    conn.close()

_init_db()

def save_to_memory(topic: str, fact: str) -> str:
    """
    Зберігає важливий факт, налаштування або преференцію користувача в довгострокову пам'ять.
    Використовуй цей інструмент, коли користувач просить тебе щось запам'ятати на майбутнє, 
    або коли ти дізнаєшся важливу деталь (наприклад, його ім'я, улюблену технологію, шлях до нового проекту).
    
    Args:
        topic: Короткий тег або категорія (наприклад, 'User Preference', 'Project Path', 'Fact').
        fact: Сам факт, який потрібно запам'ятати (наприклад, 'Користувач любить темну тему', 'Шлях до проекту Х: C:\\...').
    """
    print(f"🧠 [Memory]: Запам'ятовую факт про '{topic}'...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory (topic, fact, timestamp) VALUES (?, ?, ?)", 
            (topic, fact, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        return f"Факт про '{topic}' успішно назавжди збережено в довгострокову пам'ять."
    except Exception as e:
        return f"Помилка збереження в пам'ять: {e}"

def search_memory(query: str) -> str:
    """
    Шукає інформацію в довгостроковій пам'яті за ключовим словом або темою.
    Використовуй цей інструмент ПЕРЕД тим, як сказати "Я не знаю" або "У мене немає доступу", 
    щоб перевірити, чи не розповідав тобі користувач про це раніше.
    
    Args:
        query: Ключове слово для пошуку (наприклад, 'AuraMail', 'ім'я', 'шлях').
    """
    print(f"🧠 [Memory]: Шукаю в архівах згадки про '{query}'...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Шукаємо збіги і в темах, і в самих фактах
        cursor.execute(
            "SELECT topic, fact, timestamp FROM memory WHERE topic LIKE ? OR fact LIKE ?", 
            (f"%{query}%", f"%{query}%")
        )
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return f"В архівах пам'яті не знайдено нічого за запитом '{query}'."
        
        response = "Знайдено в пам'яті:\n"
        for row in results:
            response += f"- [{row[0]}] {row[1]} (додано: {row[2]})\n"
        return response
    except Exception as e:
        return f"Помилка пошуку в пам'яті: {e}"

# Експортуємо інструменти для Оркестратора
EXPORTED_TOOLS = [save_to_memory, search_memory]