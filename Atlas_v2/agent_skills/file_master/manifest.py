import os
import datetime
import platform
from core.i18n import lang
from core.skills.wrapper import agent_tool
from core.system.path_utils import resolve_path

@agent_tool
def list_directory(path: str, **kwargs) -> str:
    """Lists directory contents strictly using the provided path."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path') or "."
    path = resolve_path(path)

    try:
        if not os.path.exists(path): 
            parent = os.path.dirname(path) or "."
            hint = ""
            if os.path.exists(parent):
                items = os.listdir(parent)[:15]
                hint = f"\n🔍 [PATH HINT]: '{path}' not found. Parent folder '{parent}' contains: {', '.join(items)}..."
            return f"❌ [ERROR]: Directory '{path}' not found.{hint}"
            
        if os.path.isfile(path):
            return f"❌ [ERROR]: '{path}' is a FILE, not a directory. Use 'read_file' to view its content."
            
        items = os.listdir(path)
        result = f"### Directory: {path}\n"
        for item in sorted(items):
            item_path = os.path.join(path, item)
            if os.path.isdir(item_path): result += f"📁 {item}/\n"
            else:
                size = os.path.getsize(item_path)
                result += f"📄 {item} ({size} bytes)\n"
        return result
    except Exception as e: return f"Read Error: {e}"

@agent_tool
def open_item(path: str, **kwargs) -> str:
    """Opens a file, video, or folder on the user's screen (double-click)."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    path = resolve_path(path)
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
def get_file_tree(path: str = None, max_depth: int = 3, **kwargs) -> str:
    """Returns a recursive tree visualization of the project structure."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path') or "."
    path = resolve_path(path)
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
def read_file(path: str, **kwargs) -> str:
    """Reads file content safely using UTF-8. Path is REQUIRED."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    path = resolve_path(path)
    try:
        if not os.path.exists(path):
            parent = os.path.dirname(path) or "."
            hint = ""
            if os.path.exists(parent):
                items = os.listdir(parent)[:15]
                hint = f"\n🔍 [PATH HINT]: File '{path}' missing. Actual contents of '{parent}': {', '.join(items)}..."
            return f"❌ [ERROR]: File not found: {path}.{hint}"
            
        if os.path.isdir(path):
            return f"❌ [ERROR]: '{path}' is a DIRECTORY. You cannot 'read_file' on a folder. Use 'list_directory' to see its contents."
            
        size = os.path.getsize(path)
        if size > 150000: return f"⚠️ File {path} too large ({size}b). Use search_text_in_files."
        with open(path, 'r', encoding='utf-8') as f: content = f.read()
        return f"--- ABSOLUTE PATH: {path} ---\n{content}\n--- End ---"
    except UnicodeDecodeError:
        with open(path, 'r', encoding='utf-8', errors='replace') as f: content = f.read()
        return f"--- ABSOLUTE PATH: {path} (Encoding Warning: Non UTF-8 chars replaced) ---\n{content}\n--- End ---"
    except Exception as e: return f"Read Error: {e}"

@agent_tool
def write_file(path: str, content: str = "", **kwargs) -> str:
    """Overwrites or creates a file with specified content (UTF-8)."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    path = resolve_path(path)
    # [v3.6.8] Zero-Placeholder Policy Check
    content_lower = content.lower().strip()
    placeholders = ["hello world", "basic structure", "[insert here]", "todo:", "placeholder"]
    if any(p in content_lower for p in placeholders) or (len(content_lower) < 20 and not path.endswith('.txt')):
         return "❌ [SECURITY REJECTED]: Zero-Placeholder Policy Violation. AXIS is forbidden from creating stubs or empty structures. Please provide PRODUCTION-READY content."

    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
        
        # Trigger Auto-Indexing (v2.8.6)
        from core.brain.memory import memory_manager
        memory_manager.reindex_file(path)
        
        return f"✅ [FILE WRITTEN]: {path} (UTF-8)"
    except Exception as e: return f"Write Error: {e}"

@agent_tool
def append_to_file(path: str, content: str = "", **kwargs) -> str:
    """Appends content to a file. Path is REQUIRED."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    path = resolve_path(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f: f.write(content)
        
        # Trigger Auto-Indexing (v2.8.6)
        from core.brain.memory import memory_manager
        memory_manager.reindex_file(path)
        
        return f"📝 [APPEND SUCCESS]: {path} (UTF-8)"
    except Exception as e: return f"Append Error: {e}"

@agent_tool
def delete_file(path: str = None, **kwargs) -> str:
    """Deletes a file or empty directory."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    if not path: return "Error: No path provided."
    path = resolve_path(path)
    try:
        if os.path.isdir(path): os.rmdir(path)
        else: os.remove(path)
        return f"🗑️ [DELETED]: {path}"
    except Exception as e: return f"Delete Error: {e}"

@agent_tool
def search_text_in_files(query: str, root_path: str = None, **kwargs) -> str:
    """
    Project-wide 'grep' for finding text or code patterns. 
    Supports MULTI-QUERY: Separate keywords with commas (e.g., 'finance, security') for OR-search.
    """
    root_path = root_path or kwargs.get('path') or kwargs.get('file_path') or "."
    root_path = resolve_path(root_path)
    
    # [v3.8.10] Smart Multi-Query Parsing
    import re
    keywords = [k.strip() for k in re.split(r'[,;]', query) if k.strip()]
    if not keywords: keywords = [query]

    matches = []
    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in {".git", "venv", "node_modules", "__pycache__"}]
        for name in files:
            if name.endswith(('.py', '.md', '.json', '.yaml', '.txt', '.js', '.css', '.html')):
                fpath = os.path.join(root, name)
                try:
                    with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                        for i, line in enumerate(f, 1):
                            line_content = line.strip()
                            # Check for any keyword (OR logic)
                            for kw in keywords:
                                if kw.lower() in line_content.lower():
                                    matches.append(f"{os.path.relpath(fpath, root_path)}:{i}: [{kw}] {line_content[:150]}")
                                    break # One match per line is enough
                            if len(matches) > 50: return "### Top 50 Results:\n" + "\n".join(matches)
                except Exception: continue
    
    res = "### Search Results:\n" + "\n".join(matches) if matches else f"No matches found for any of: {keywords}"
    return res

@agent_tool
def get_file_info(path: str = None, **kwargs) -> str:
    """Returns metadata (size, dates) for a file."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    if not path: return "Error: No path provided."
    path = resolve_path(path)
    if not os.path.exists(path): return "File not found."
    stats = os.stat(path)
    return f"### {path} Info:\nSize: {stats.st_size} bytes\nModified: {datetime.datetime.fromtimestamp(stats.st_mtime)}"

@agent_tool
def make_directory(path: str = None, **kwargs) -> str:
    """Creates a directory and its parents if needed."""
    path = path or kwargs.get('file_path') or kwargs.get('item_path')
    if not path: return "Error: No path provided."
    path = resolve_path(path)
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ [MKDIR SUCCESS]: {path}"
    except Exception as e:
        return f"Error creating directory {path}: {e}"

@agent_tool
def copy_file(source: str = None, destination: str = None, **kwargs) -> str:
    """Copies a file to a new location."""
    source = source or kwargs.get('src') or kwargs.get('from')
    destination = destination or kwargs.get('dest') or kwargs.get('to')
    if not source or not destination: return "Error: Source and destination required."
    
    source = resolve_path(source)
    destination = resolve_path(destination)
    
    try:
        import shutil
        if not os.path.exists(source):
            return f"Error: Source {source} not found."
            
        # If destination is a directory, preserve filename
        if os.path.isdir(destination):
            destination = os.path.join(destination, os.path.basename(source))
        else:
            # Ensure parent dir exists
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
        shutil.copy2(source, destination)
        return f"✅ [COPIED]: {source} -> {destination}"
    except Exception as e:
        return f"Copy Error: {e}"

@agent_tool
def replace_file_content(path: str, target_text: str, replacement_text: str, **kwargs) -> str:
    """
    [v3.8.12] Universal Text Patcher (Grep-based replacement). 
    Replaces a specific string block with new text in ANY file (.md, .sql, .env, .py).
    Does NOT require AST. Ideal for non-Python files or simple changes.
    """
    path = resolve_path(path)
    if not os.path.exists(path):
        parent = os.path.dirname(path) or "."
        hint = ""
        if os.path.exists(parent):
            hint = f"\n🔍 [PATH HINT]: Parent '{parent}' contains: {os.listdir(parent)[:10]}"
        return f"❌ [ERROR]: File not found: {path}.{hint}"

    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        if target_text not in content:
            return f"❌ [REPLACE FAILED]: Target text not found in '{path}'. Use EXACT string for target_text."

        # Replace first occurrence by default (Safer)
        new_content = content.replace(target_text, replacement_text, 1)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        from core.brain.memory import memory_manager
        memory_manager.reindex_file(path)
        return f"✅ [TEXT PATCHED]: Updated file '{path}'."
    except Exception as e:
        return f"❌ [PATCH ERROR]: {str(e)}"

EXPORTED_TOOLS = [list_directory, open_item, get_file_tree, read_file, write_file, append_to_file, delete_file, search_text_in_files, get_file_info, make_directory, copy_file, replace_file_content]
