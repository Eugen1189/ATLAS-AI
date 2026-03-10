import os
import subprocess
from core.system.discovery import EnvironmentDiscoverer
from pathlib import Path

def open_workspace(project: str, ide: str = None) -> str:
    """Standard 2026 Workspace Loader. Autodetects IDEs and project paths."""
    disc = EnvironmentDiscoverer()
    f = disc.run_full_discovery(store_in_memory=False)
    target = None
    for ws in f.get("workspaces", []):
        p = Path(ws)
        if p.name.lower() == project.lower(): target = str(p); break
        try:
            for sub in p.iterdir():
                if sub.is_dir() and sub.name.lower() == project.lower(): target = str(sub); break
        except Exception: pass
        if target: break
    if not target: return f"Error: Project '{project}' not found."
    
    # IDE Select
    installed = f.get("ides", {})
    if not ide:
        ide = "Cursor" if "Cursor" in installed else "VS Code" if "VS Code" in installed else "Explorer"
    cmd = "cursor" if ide == "Cursor" else "code" if ide == "VS Code" else "explorer"
    subprocess.Popen(f'{cmd} "{target}"', shell=True)
    return f"🚀 [PROJECT READY]: '{project}' opened in {ide}."

def setup_new_project(name: str) -> str:
    """Standard 2026 Scaffold: Creates a specialized folder structure."""
    disc = EnvironmentDiscoverer()
    ws = disc.run_full_discovery(store_in_memory=False).get("primary_workspace")
    if not ws: return "Err: No workspace."
    path = os.path.join(ws, name)
    try:
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        os.makedirs(os.path.join(path, "tests"), exist_ok=True)
        with open(os.path.join(path, "README.md"), "w") as f: f.write(f"# {name} (AXIS)")
        return f"✨ [INIT DONE]: project {name} created."
    except Exception as e: return f"Err: {e}"

def get_workspace_summary() -> str:
    """Returns a full audit of currently tracked workspaces and projects."""
    disc = EnvironmentDiscoverer()
    f = disc.run_full_discovery(store_in_memory=False)
    ws = f.get("workspaces", [])
    return f"### Workspaces Diagnostic:\nPrimary: {f.get('primary_workspace')}\nTracked: {ws}"

EXPORTED_TOOLS = [open_workspace, setup_new_project, get_workspace_summary]
