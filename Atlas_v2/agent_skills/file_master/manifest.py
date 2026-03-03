import os
from core.i18n import lang

def list_directory(path: str = ".") -> str:
    """
    Lists the contents of the specified directory (files and subfolders).
    Use this tool when you need to understand project structure,
    find a specific file, or check if a directory exists.
    
    Args:
        path: Path to the folder (defaults to current directory).
    """
    print(lang.get("file_master.reading_dir", path=path))
    try:
        if not os.path.exists(path):
            return lang.get("file_master.dir_not_found", path=path)
        
        items = os.listdir(path)
        result = f"Contents of folder '{path}':\n"
        for item in items:
            item_path = os.path.join(path, item)
            item_type = "[DIR ]" if os.path.isdir(item_path) else "[FILE]"
            result += f"- {item_type} {item}\n"
        return result
    except Exception as e:
        return lang.get("file_master.read_error", error=e)

def read_file(filepath: str) -> str:
    """
    Reads the content of a text or code file (.py, .txt, .md, .json etc).
    Use this tool to analyze existing code before proposing changes.
    
    Args:
        filepath: Full or relative path to the file.
    """
    print(lang.get("file_master.reading_file", path=filepath))
    try:
        if not os.path.exists(filepath):
            return lang.get("file_master.file_not_found", path=filepath)
            
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        return f"--- Start of file {filepath} ---\n{content}\n--- End of file ---"
    except Exception as e:
        return lang.get("file_master.file_read_error", error=e)

def write_file(filepath: str, content: str) -> str:
    """
    Creates a new file or COMPLETELY overwrites an existing one with the given text/code.
    Use this tool to create new scripts or apply refactoring.
    
    Args:
        filepath: Path where to save the file.
        content: Text or code to write.
    """
    print(lang.get("file_master.writing_file", lines=len(content.splitlines()), path=filepath))
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return lang.get("file_master.file_written", bytes=len(content.encode('utf-8')), path=filepath)
    except Exception as e:
        return lang.get("file_master.file_write_error", error=e)

# Export tools for Orchestrator
EXPORTED_TOOLS = [list_directory, read_file, write_file]