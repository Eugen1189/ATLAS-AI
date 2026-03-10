import os
import json
import datetime
import platform
from core.i18n import lang
from core.skills.wrapper import agent_tool

def _resolve_path(path: str) -> str:
    """Helper to expand home, handle Windows shell folders, and placeholders."""
    if not path: return os.path.abspath(".")
    
    # Placeholder fix
    path = path.replace("[Your_Username]", os.getlogin())
    
    # Magic words for Windows
    magic_folders = {
        "Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "Documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "Music": os.path.join(os.path.expanduser("~"), "Music"),
        "Pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "Videos": os.path.join(os.path.expanduser("~"), "Videos"),
    }
    
    # Check if path starts with a magic word
    for word, real_path in magic_folders.items():
        if path.startswith(word):
            path = path.replace(word, real_path, 1)
            break
            
    return os.path.abspath(os.path.expanduser(path))

@agent_tool
def list_directory(path: str = ".") -> str:
    """Lists the contents of the specified directory. Supports keywords like 'Desktop'."""
    path = _resolve_path(path)
    try:
        if not os.path.exists(path): return lang.get("file_master.dir_not_found", path=path)
        items = os.listdir(path)
        result = f"### Directory: {path}\n"
        for item in sorted(items):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path): result += f"📁 {item}/\n"
            else:
                size = os.path.getsize(item_path)
                result += f"📄 {item} ({size} bytes)\n"
        return result
    except Exception as e: return lang.get("file_master.read_error", error=e)

@agent_tool
def open_item(filepath: str) -> str:
    """FHYISICALLY OPENS a file, video, or folder on the user screen. Like a double-click."""
    path = _resolve_path(filepath)
    if not os.path.exists(path): return f"Error: Path {path} not found."
    
    try:
        if platform.system() == "Windows":
            os.startfile(path)
            return f"✅ [OPENED]: {path}"
        else:
            return "Error: open_item is only supported on Windows."
    except Exception as e:
        return f"failed to open {path}: {e}"

@agent_tool
def get_file_tree(path: str = ".", max_depth: int = 3) -> str:
    """Returns a recursive tree visualization of the project structure."""
    path = _resolve_path(path)
    result = [f"### Project Tree: {path}"]
    def _recruit(current_path, indent, depth):
        if depth > max_depth: return
        try:
            for item in sorted(os.listdir(current_path)):
                if item in {".git", "__pycache__", "venv", "node_modules"}: continue
                item_path = os.path.join(current_path, item)
                prefix = "  " * indent + ("└── " if indent > 0 else "")
                if os.path.isdir(item_path):
                    result.append(f"{prefix}📁 {item}/")
                    _recruit(item_path, indent + 1, depth + 1)
                else: result.append(f"{prefix}📄 {item}")
        except Exception: pass
    _recruit(path, 0, 1)
    return "\n".join(result)

@agent_tool
def read_file(filepath: str) -> str:
    """Reads content of a file. Protects context from overflow."""
    filepath = _resolve_path(filepath)
    try:
        if not os.path.exists(filepath): return lang.get("file_master.file_not_found", path=filepath)
        size = os.path.getsize(filepath)
        if size > 150000: return f"⚠️ File {filepath} too large ({size}b). Use search_text_in_files."
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
        return f"--- {filepath} ---\n{content}\n--- End ---"
    except Exception as e: return f"Read Error: {e}"

@agent_tool
def write_file(filepath: str, content: str) -> str:
    """Completely overwrites/creates a file with content. Supports magic keywords."""
    filepath = _resolve_path(filepath)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f: f.write(content)
        return f"✅ [FILE WRITTEN]: {filepath}"
    except Exception as e: return f"Write Error: {e}"

@agent_tool
def append_to_file(filepath: str, content: str) -> str:
    """Appends content to a file."""
    filepath = _resolve_path(filepath)
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'a', encoding='utf-8') as f: f.write(content)
        return f"📝 [APPEND SUCCESS]: {filepath}"
    except Exception as e: return f"Append Error: {e}"

@agent_tool
def delete_file(filepath: str) -> str:
    """Deletes a file or empty directory."""
    filepath = _resolve_path(filepath)
    try:
        if os.path.isdir(filepath): os.rmdir(filepath)
        else: os.remove(filepath)
        return f"🗑️ [DELETED]: {filepath}"
    except Exception as e: return f"Delete Error: {e}"

@agent_tool
def search_text_in_files(query: str, root_path: str = ".") -> str:
    """Project-wide 'grep' for finding text or code patterns."""
    root_path = _resolve_path(root_path)
    matches = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in {".git", "venv", "node_modules"}]
        for name in files:
            if name.endswith(('.py', '.md', '.json', '.yaml', '.txt', '.js')):
                fpath = os.path.join(root, name)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            if query in line:
                                matches.append(f"{os.path.relpath(fpath, root_path)}:{i}: {line.strip()[:100]}")
                                if len(matches) > 30: return "### Top 30 Results:\n" + "\n".join(matches)
                except Exception: continue
    return "### Search Results:\n" + "\n".join(matches) if matches else f"No matches for '{query}'"

@agent_tool
def get_file_info(filepath: str) -> str:
    """Returns metadata (size, dates) for a file."""
    filepath = _resolve_path(filepath)
    if not os.path.exists(filepath): return "File not found."
    stats = os.stat(filepath)
    return f"### {filepath} Info:\nSize: {stats.st_size} bytes\nModified: {datetime.datetime.fromtimestamp(stats.st_mtime)}"

EXPORTED_TOOLS = [list_directory, open_item, get_file_tree, read_file, write_file, append_to_file, delete_file, search_text_in_files, get_file_info]
