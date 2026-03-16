import os
import subprocess
from core.system.discovery import EnvironmentDiscoverer
from pathlib import Path
from core.skills.wrapper import agent_tool

@agent_tool
def open_workspace(project: str, ide: str = None, **kwargs) -> str:
    """Standard 2026 Workspace Loader. Autodetects IDEs and project paths."""
    # [PROTOCOL 2.0] Path support: if 'project' is an existing directory, use it directly
    if os.path.isdir(project):
        target = str(Path(project).resolve())
        project_name = Path(project).name
    else:
        disc = EnvironmentDiscoverer()
        f = disc.run_full_discovery(store_in_memory=False)
        target = None
        project_name = project
        for ws in f.get("workspaces", []):
            p = Path(ws)
            if p.name.lower() == project.lower(): target = str(p); break
            try:
                for sub in p.iterdir():
                    if sub.is_dir() and sub.name.lower() == project.lower(): target = str(sub); break
            except Exception: pass
            if target: break
            
    if not target: return f"❌ Error: Project '{project}' not found. Try searching for available workspaces with 'get_workspace_summary'."
    
    # IDE Select
    installed = EnvironmentDiscoverer().run_full_discovery(store_in_memory=False).get("ides", {})
    if not ide:
        # [PROTOCOL 2.0] Context Awareness: Detect if we are already in Antigravity
        if os.getenv("ANTIGRAVITY_AGENT") == "1" or "Antigravity" in installed:
            ide = "Antigravity"
        else:
            ide = "Cursor" if "Cursor" in installed else "VS Code" if "VS Code" in installed else "Explorer"
    
    # CLI command mapping
    antigravity_path = os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Antigravity", "antigravity.exe")
    cmd_map = {
        "Antigravity": antigravity_path if os.path.exists(antigravity_path) else "antigravity",
        "Cursor": "cursor",
        "VS Code": "code",
        "Explorer": "explorer"
    }
    cmd = cmd_map.get(ide, "explorer")
    
    try:
        subprocess.Popen(f'{cmd} "{target}"', shell=True)
        return f"🚀 [PROJECT READY]: '{project_name}' opened in {ide}."
    except Exception as e:
        return f"❌ Error during opening: {e}"

@agent_tool
def setup_new_project(name: str, **kwargs) -> str:
    """Standard 2026 Scaffold: Creates a specialized folder structure."""
    disc = EnvironmentDiscoverer()
    ws = disc.run_full_discovery(store_in_memory=False).get("primary_workspace")
    if not ws: return "❌ Error: No workspace detected."
    path = os.path.join(ws, name)
    try:
        os.makedirs(os.path.join(path, "src"), exist_ok=True)
        os.makedirs(os.path.join(path, "tests"), exist_ok=True)
        with open(os.path.join(path, "README.md"), "w") as f: f.write(f"# {name} (AXIS)")
        return f"✨ [INIT DONE]: project {name} created."
    except Exception as e: return f"❌ Error: {e}"

@agent_tool
def get_workspace_summary(**kwargs) -> str:
    """Returns a full audit of currently tracked workspaces and projects."""
    disc = EnvironmentDiscoverer()
    f = disc.run_full_discovery(store_in_memory=False)
    ws = f.get("workspaces", [])
    return f"### Workspaces Diagnostic:\nPrimary: {f.get('primary_workspace')}\nTracked: {ws}"

EXPORTED_TOOLS = [open_workspace, setup_new_project, get_workspace_summary]

