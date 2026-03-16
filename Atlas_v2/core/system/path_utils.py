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
        if not test_path.exists():
            # Strategy: 2. Try as a sibling to Atlas (C:/Projects/...)
            sibling_path = root.parent / p
            if sibling_path.exists():
                p = sibling_path
            else:
                p = test_path
        else:
            p = test_path
        
    return str(p.resolve())
