import os
from pathlib import Path
from dotenv import load_dotenv

def get_project_root() -> Path:
    """Returns the absolute path to the project root (where .env and Atlas_v2 live)."""
    # Assuming this file is in Atlas_v2/core/system/path_utils.py
    return Path(__file__).parent.parent.parent.parent.resolve()

def load_environment():
    """Ensures .env is loaded from the project root."""
    root = get_project_root()
    env_path = root / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=str(env_path))

def resolve_path(path: str) -> str:
    """
    Expands home, handles Windows magic folders, and placeholders.
    Ensures relative paths are relative to the project root.
    """
    if not path:
        return str(get_project_root())
    
    # Handle [Your_Username] placeholder (common in v2 blueprints)
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
            
    # Resolve relative to root if not absolute
    p = Path(os.path.expanduser(path))
    if not p.is_absolute():
        p = get_project_root() / p
        
    return str(p.resolve())
