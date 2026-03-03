import sqlite3
import os
from datetime import datetime
from core.i18n import lang

# Define path to the database in the memories folder
current_dir = os.path.dirname(os.path.abspath(__file__))
db_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "memories"))
os.makedirs(db_dir, exist_ok=True)
DB_PATH = os.path.join(db_dir, "axis_memory.db")

# Automatic table creation on first launch
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
    Saves an important fact, setting, or user preference into long-term memory.
    Use this tool when the user asks you to remember something for the future,
    or when you learn an important detail (e.g., their name, favorite tech, path to new project).
    
    Args:
        topic: A short tag or category (e.g., 'User Preference', 'Project Path', 'Fact').
        fact: The fact itself to be remembered (e.g., 'User likes dark theme', 'Project X path: C:\\...').
    """
    print(lang.get("memory.remembering", topic=topic))
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO memory (topic, fact, timestamp) VALUES (?, ?, ?)", 
            (topic, fact, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        conn.commit()
        conn.close()
        return lang.get("memory.fact_saved", topic=topic)
    except Exception as e:
        return lang.get("memory.save_error", error=e)

def search_memory(query: str) -> str:
    """
    Searches for information in long-term memory by keyword or topic.
    Use this tool BEFORE saying "I don't know" or "I don't have access",
    to check if the user has told you about this before.
    
    Args:
        query: Keyword for search (e.g., 'AuraMail', 'name', 'path').
    """
    print(lang.get("memory.searching", query=query))
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Search for matches in both topics and facts
        cursor.execute(
            "SELECT topic, fact, timestamp FROM memory WHERE topic LIKE ? OR fact LIKE ?", 
            (f"%{query}%", f"%{query}%")
        )
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return lang.get("memory.nothing_found", query=query)
        
        response = lang.get("memory.found")
        for row in results:
            response += f"- [{row[0]}] {row[1]} (added: {row[2]})\n"
        return response
    except Exception as e:
        return lang.get("memory.search_error", error=e)

# Export tools for Orchestrator
EXPORTED_TOOLS = [save_to_memory, search_memory]