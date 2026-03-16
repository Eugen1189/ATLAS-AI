import sqlite3
import os
from core.skills.wrapper import agent_tool
from core.system.path_utils import resolve_path

@agent_tool
def query_database(db_path: str, sql: str, **kwargs) -> str:
    """Executes a SQL query on a local SQLite database and returns results. Use this instead of terminal 'sqlite3'."""
    db_path = resolve_path(db_path)
    if not os.path.exists(db_path):
        return f"Error: Database file not found at {db_path}"
    
    try:
        conn = sqlite3.connect(db_path)
        # Use Row factory for better output
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(sql)
        
        if sql.strip().upper().startswith("SELECT"):
            rows = cursor.fetchall()
            if not rows:
                return "Query executed successfully. No rows returned."
            
            # Format results as a neat table
            keys = rows[0].keys()
            header = " | ".join(keys)
            separator = "-+-".join(["-" * len(k) for k in keys])
            result_lines = [header, separator]
            for row in rows:
                result_lines.append(" | ".join(str(row[k]) for k in keys))
            
            return "\n".join(result_lines)
        else:
            conn.commit()
            affected = conn.total_changes
            return f"✅ SQL executed successfully. Rows affected: {affected}"
            
    except Exception as e:
        return f"❌ SQL ERROR: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()

@agent_tool
def get_db_schema(db_path: str, **kwargs) -> str:
    """Returns the schema (tables and columns) of a SQLite database."""
    db_path = resolve_path(db_path)
    if not os.path.exists(db_path):
        return f"Error: Database file not found at {db_path}"
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            return "The database is empty (no tables found)."
            
        result = [f"### Database Schema: {os.path.basename(db_path)}"]
        for table in tables:
            table_name = table[0]
            result.append(f"\n📂 Table: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for col in columns:
                # col[1] = name, col[2] = type
                result.append(f"  - {col[1]} ({col[2]})")
                
        return "\n".join(result)
    except Exception as e:
        return f"❌ Error reading schema: {str(e)}"
    finally:
        if 'conn' in locals():
            conn.close()

EXPORTED_TOOLS = [query_database, get_db_schema]
