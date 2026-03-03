import os
from core.i18n import lang

# This description (docstring) is critically important! Gemini reads it.
def open_workspace(project_name: str) -> str:
    """
    Searches for a project on the C: drive and opens it in Cursor IDE and the browser.
    Use this tool when the user asks to "open project", 
    "deploy workspace", or "prepare environment" for a specific project.
    
    Args:
        project_name: Project name to search for (e.g., 'SystemCOO', 'AuraMail').
    """
    print(lang.get("workspace.searching", project=project_name))
    
    # Our optimized search for today
    root_dir = "C:\\Users\\Eugen1189\\"
    for r, d, f in os.walk(root_dir):
        if project_name.lower() in [dir.lower() for dir in d]:
            target_path = os.path.join(r, project_name)
            
            # Open the folder and Cursor
            os.startfile(target_path)
            os.system(f'cursor "{target_path}"')
            
            # Can add opening Perplexity, as we did
            os.system('start https://www.perplexity.ai/')
            
            return lang.get("workspace.success", project=project_name, path=target_path)
            
    return lang.get("workspace.not_found", project=project_name)

# Export the list of tools this skill provides to the Core
EXPORTED_TOOLS = [open_workspace]