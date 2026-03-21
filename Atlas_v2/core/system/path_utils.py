import os
from pathlib import Path
from dotenv import load_dotenv

def get_project_root() -> Path:
    """Returns the absolute path to the project root (where .env and Atlas_v2 live)."""
    # [ROBUST v3.6.0] Upward search for markers
    current_file = Path(__file__).resolve()
    # Start looking from the parent directory of this file
    for parent in current_file.parents:
        if parent.is_dir() and ((parent / ".env").exists() or (parent / "Atlas_v2").exists() or (parent / ".git").exists()):
            return parent
    
    # Fallback: assume standard structure or CWD
    return Path(os.getcwd()).resolve()

def get_namespace_for_path(path: str) -> str:
    """Creates a unique, reproducible namespace for a directory path (v3.5.0)."""
    import hashlib
    abs_path = os.path.abspath(path).lower()
    path_hash = hashlib.sha256(abs_path.encode()).hexdigest()[:8]
    folder_name = os.path.basename(abs_path)
    return f"{folder_name}_{path_hash}"

def load_environment():
    """Ensures .env is loaded from the project root."""
    root = get_project_root()
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))
    
    # [FORCE UTF-8] (v3.5.0)
    os.environ["PYTHONIOENCODING"] = "utf-8"

def resolve_path(path: str) -> str:
    """
    Expands home, handles Windows magic folders, and placeholders.
    Ensures relative paths are resolved absolutely.
    If not found in root, checks one level up (sibling projects).
    """
    if not path:
        return str(get_project_root())
    
    # Handle [Your_Username] placeholder
    try:
        path = path.replace("[Your_Username]", os.getlogin())
    except:
        pass
    
    # Expand Windows magic folders
    magic_folders = {
        "Desktop": os.path.join(os.path.expanduser("~"), "Desktop"),
        "Documents": os.path.join(os.path.expanduser("~"), "Documents"),
        "Downloads": os.path.join(os.path.expanduser("~"), "Downloads"),
        "Music": os.path.join(os.path.expanduser("~"), "Music"),
        "Pictures": os.path.join(os.path.expanduser("~"), "Pictures"),
        "Videos": os.path.join(os.path.expanduser("~"), "Videos"),
    }
    
    for word, real_path in magic_folders.items():
        if path.startswith(word):
            path = path.replace(word, real_path, 1)
            break
            
    p = Path(os.path.expanduser(path))
    if not p.is_absolute():
        root = get_project_root()
        # Strategy: 1. Try relative to Atlas root
        test_path = root / p
        
        # Strategy: 2. Sibling project lookup (RESTRICTED - only if exists)
        # Avoid guessing new projects here.
        if not test_path.exists():
            sibling_path = root.parent / p
            if sibling_path.exists() and os.path.isdir(sibling_path):
                p = sibling_path
            else:
                p = test_path
        else:
            p = test_path
        
    return str(p.resolve())
