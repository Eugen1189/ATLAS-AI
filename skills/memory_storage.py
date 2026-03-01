"""
skills/memory_storage.py
Система довгострокової пам'яті для ATLAS.

Зберігає:
- Нагадування та дедлайни
- Важливі факти
- Проекти та задачі
"""

import sqlite3
import json
import os
import datetime
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Додаємо батьківську директорію для імпортів
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if True:
    try:
        import config
    except ImportError:
        # Fallback if config is not available directly
        class DummyConfig:
            MEMORIES_DIR = Path("memories")
            MEMORY_STORAGE_FILE = Path("memories/atlas_memory.json")
        config = DummyConfig()


@dataclass
class MemoryEntry:
    """Запис пам'яті"""
    id: str
    type: str  # "reminder", "fact", "deadline", "project"
    content: str
    date_created: str
    date_due: Optional[str] = None  # Для дедлайнів
    tags: List[str] = None
    metadata: Dict = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if isinstance(self.tags, str):
            try:
                self.tags = json.loads(self.tags)
            except:
                self.tags = [self.tags]
        if self.metadata is None:
            self.metadata = {}
        if isinstance(self.metadata, str):
            try:
                self.metadata = json.loads(self.metadata)
            except:
                self.metadata = {}


class MemoryStorage:
    """
    Система збереження довгострокової пам'яті на базі SQLite.
    """
    
    def __init__(self, db_file: Optional[str] = None):
        """
        Ініціалізація системи пам'яті.
        """
        if db_file:
            self.db_path = Path(db_file)
        else:
            self.db_path = config.MEMORIES_DIR / "atlas.db"
            
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        
        # Перевірка та міграція даних з JSON
        self.migrate_from_json()
        
        print(f"[MEMORY] Система пам'яті SQLite ініціалізована ({self.db_path})")
    
    def _create_tables(self):
        """Створює таблиці та індекси"""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                type TEXT,
                content TEXT,
                date_created TEXT,
                date_due TEXT,
                tags TEXT,
                metadata TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS intent_cache (
                query_hash TEXT PRIMARY KEY,
                original_query TEXT,
                response TEXT,
                expires_at TIMESTAMP
            )
        """)
        # Створюємо індекси для швидкого пошуку
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_date_due ON memories(date_due)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_tags ON memories(tags)")
        self.conn.commit()

    def get_cached_intent(self, query: str) -> Optional[str]:
        """Отримує результат з кешу інтентів, якщо він не застарів."""
        import hashlib
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        now = datetime.datetime.now().isoformat()
        
        cursor = self.conn.execute(
            "SELECT response FROM intent_cache WHERE query_hash = ? AND expires_at > ?",
            (query_hash, now)
        )
        row = cursor.fetchone()
        if row:
            print(f"🚀 [MEMORY] SQLite Cache Hit: {query[:30]}...")
            return row['response']
        return None

    def save_intent_cache(self, query: str, response: str, ttl_seconds: int = 3600):
        """Зберігає результат в кеш інтентів."""
        import hashlib
        query_hash = hashlib.md5(query.lower().strip().encode()).hexdigest()
        expires_at = (datetime.datetime.now() + datetime.timedelta(seconds=ttl_seconds)).isoformat()
        
        self.conn.execute("""
            INSERT OR REPLACE INTO intent_cache (query_hash, original_query, response, expires_at)
            VALUES (?, ?, ?, ?)
        """, (query_hash, query, response, expires_at))
        self.conn.commit()

    def get_project_context(self, project_name: str, limit: int = 5) -> str:
        """Оптимізоване отримання контексту тільки по конкретному проекту."""
        cursor = self.conn.execute(
            "SELECT content, type FROM memories WHERE (content LIKE ? OR tags LIKE ?) ORDER BY date_created DESC LIMIT ?",
            (f'%{project_name}%', f'%{project_name}%', limit)
        )
        rows = cursor.fetchall()
        if not rows:
            return ""
        
        context_parts = [f"Знайдено в пам'яті по проекту '{project_name}':"]
        for row in rows:
            context_parts.append(f"- [{row['type'].upper()}] {row['content']}")
        
        return "\n".join(context_parts)

    def migrate_from_json(self):
        """Мігрує дані з старого atlas_memory.json, якщо він існує"""
        json_path = config.MEMORY_STORAGE_FILE
        if os.path.exists(json_path):
            print(f"[MEMORY] Знайдено застарілий файл {json_path}. Починаю міграцію...")
            try:
                with open(json_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    memories = data.get('memories', [])
                    
                count = 0
                for entry in memories:
                    # Перевіряємо чи вже існує
                    cursor = self.conn.execute("SELECT id FROM memories WHERE id = ?", (entry['id'],))
                    if not cursor.fetchone():
                        self.conn.execute("""
                            INSERT INTO memories (id, type, content, date_created, date_due, tags, metadata)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (
                            entry['id'], 
                            entry['type'], 
                            entry['content'], 
                            entry['date_created'], 
                            entry.get('date_due'),
                            json.dumps(entry.get('tags', [])),
                            json.dumps(entry.get('metadata', {}))
                        ))
                        count += 1
                
                self.conn.commit()
                if count > 0:
                    print(f"✅ [MEMORY] Мігровано {count} записів з JSON до SQLite.")
                
                # Перейменовуємо старий файл, щоб не мігрувати знову
                backup_path = json_path.with_suffix('.json.bak')
                os.rename(json_path, backup_path)
                print(f"[MEMORY] Старий файл перейменовано на {backup_path}")
                
            except Exception as e:
                print(f"❌ [MEMORY] Помилка міграції: {e}")

    def save_reminder(self, content: str, date_due: Optional[str] = None, tags: List[str] = None) -> str:
        """Зберігає нагадування або дедлайн."""
        entry_id = f"reminder_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        parsed_date = self._parse_date(date_due) if date_due else None
        
        date_created = datetime.datetime.now().isoformat()
        date_due_str = parsed_date.isoformat() if parsed_date else None
        tags_json = json.dumps(tags or [])
        m_type = "deadline" if parsed_date else "reminder"
        
        self.conn.execute("""
            INSERT INTO memories (id, type, content, date_created, date_due, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (entry_id, m_type, content, date_created, date_due_str, tags_json, "{}"))
        self.conn.commit()
        
        print(f"[MEMORY] SQLite: Збережено {m_type}")
        return entry_id
    
    def save_fact(self, content: str, tags: List[str] = None) -> str:
        """Зберігає важливий факт."""
        entry_id = f"fact_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        date_created = datetime.datetime.now().isoformat()
        tags_json = json.dumps(tags or [])
        
        self.conn.execute("""
            INSERT INTO memories (id, type, content, date_created, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (entry_id, "fact", content, date_created, tags_json, "{}"))
        self.conn.commit()
        
        print(f"[MEMORY] SQLite: Збережено факт")
        return entry_id
    
    def get_deadlines(self, upcoming_days: int = 30) -> List[MemoryEntry]:
        """Отримує дедлайни на найближчі дні використовуючи SQL фільтрацію."""
        today = datetime.date.today().isoformat()
        end_date = (datetime.date.today() + datetime.timedelta(days=upcoming_days)).isoformat()
        
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE type = 'deadline' AND date_due BETWEEN ? AND ? ORDER BY date_due ASC",
            (today, end_date)
        )
        return [MemoryEntry(**dict(row)) for row in cursor.fetchall()]
    
    def get_reminders(self) -> List[MemoryEntry]:
        """Отримує всі нагадування."""
        cursor = self.conn.execute("SELECT * FROM memories WHERE type = 'reminder' ORDER BY date_created DESC")
        return [MemoryEntry(**dict(row)) for row in cursor.fetchall()]
    
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Пошук через SQL (набагато швидше за лінійний цикл)."""
        cursor = self.conn.execute(
            "SELECT * FROM memories WHERE content LIKE ? OR tags LIKE ? COLLATE NOCASE LIMIT ?",
            (f'%{query}%', f'%{query}%', limit)
        )
        return [MemoryEntry(**dict(row)) for row in cursor.fetchall()]
    
    def _parse_date(self, date_str: str) -> Optional[datetime.date]:
        """Парсить дату (залишено стару логіку)."""
        date_str_lower = date_str.lower().strip()
        try:
            return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            pass
        
        weekdays = {
            "понеділок": 0, "вівторок": 1, "середа": 2, "четвер": 3,
            "п'ятниця": 4, "субота": 5, "неділя": 6
        }
        
        if date_str_lower in weekdays:
            today = datetime.date.today()
            target_weekday = weekdays[date_str_lower]
            days_ahead = target_weekday - today.weekday()
            if days_ahead <= 0: days_ahead += 7
            return today + datetime.timedelta(days=days_ahead)
        
        if "через" in date_str_lower:
            import re
            match = re.search(r'(\d+)', date_str_lower)
            if match:
                days = int(match.group(1))
                return datetime.date.today() + datetime.timedelta(days=days)
        return None
    
    def delete_entry(self, entry_id: str) -> bool:
        """Видаляє запис за ID."""
        cursor = self.conn.execute("DELETE FROM memories WHERE id = ?", (entry_id,))
        self.conn.commit()
        return cursor.rowcount > 0


# Глобальний екземпляр
_memory_storage = None

def get_memory_storage() -> MemoryStorage:
    global _memory_storage
    if _memory_storage is None:
        _memory_storage = MemoryStorage()
    return _memory_storage
