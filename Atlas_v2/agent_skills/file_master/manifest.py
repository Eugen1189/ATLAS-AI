import os
import datetime
import platform
from core.i18n import lang
from core.skills.wrapper import agent_tool
from core.system.path_utils import resolve_path

@agent_tool
def list_directory(path: str = ".", **kwargs) -> str:
    """Lists directory contents. Supports keywords like 'Desktop'."""
    path = resolve_path(path)

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
def open_item(path: str, **kwargs) -> str:
    """Opens a file, video, or folder on the user's screen (double-click)."""
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
def get_file_tree(path: str = ".", max_depth: int = 3, **kwargs) -> str:
    """Returns a recursive tree visualization of the project structure."""
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
    """Reads file content. Large files trigger warning for search tool."""
    path = resolve_path(path)
    try:
        if not os.path.exists(path): return lang.get("file_master.file_not_found", path=path)
        size = os.path.getsize(path)
        if size > 150000: return f"⚠️ File {path} too large ({size}b). Use search_text_in_files."
        with open(path, 'r', encoding='utf-8', errors='ignore') as f: content = f.read()
        return f"--- {path} ---\n{content}\n--- End ---"
    except Exception as e: return f"Read Error: {e}"

@agent_tool
def write_file(path: str, content: str, **kwargs) -> str:
    """Overwrites or creates a file with specified content."""
    path = resolve_path(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f: f.write(content)
        
        # Trigger Auto-Indexing (v2.8.6)
        from core.brain.memory import memory_manager
        memory_manager.reindex_file(path)
        
        return f"✅ [FILE WRITTEN]: {path}"
    except Exception as e: return f"Write Error: {e}"

@agent_tool
def append_to_file(path: str, content: str, **kwargs) -> str:
    """Appends content to a file."""
    path = resolve_path(path)
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'a', encoding='utf-8') as f: f.write(content)
        
        # Trigger Auto-Indexing (v2.8.6)
        from core.brain.memory import memory_manager
        memory_manager.reindex_file(path)
        
        return f"📝 [APPEND SUCCESS]: {path}"
    except Exception as e: return f"Append Error: {e}"

@agent_tool
def delete_file(path: str, **kwargs) -> str:
    """Deletes a file or empty directory."""
    path = resolve_path(path)
    try:
        if os.path.isdir(path): os.rmdir(path)
        else: os.remove(path)
        return f"🗑️ [DELETED]: {path}"
    except Exception as e: return f"Delete Error: {e}"

@agent_tool
def search_text_in_files(query: str, root_path: str = ".", **kwargs) -> str:
    """Project-wide 'grep' for finding text or code patterns."""
    root_path = resolve_path(root_path)
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
def get_file_info(path: str, **kwargs) -> str:
    """Returns metadata (size, dates) for a file."""
    path = resolve_path(path)
    if not os.path.exists(path): return "File not found."
    stats = os.stat(path)
    return f"### {path} Info:\nSize: {stats.st_size} bytes\nModified: {datetime.datetime.fromtimestamp(stats.st_mtime)}"

@agent_tool
def make_directory(path: str, **kwargs) -> str:
    """Creates a directory and its parents if needed."""
    path = resolve_path(path)
    try:
        os.makedirs(path, exist_ok=True)
        return f"✅ [MKDIR SUCCESS]: {path}"
    except Exception as e:
        return f"Error creating directory {path}: {e}"

@agent_tool
def copy_file(source: str, destination: str, **kwargs) -> str:
    """Copies a file to a new location."""
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

EXPORTED_TOOLS = [list_directory, open_item, get_file_tree, read_file, write_file, append_to_file, delete_file, search_text_in_files, get_file_info, make_directory, copy_file]
