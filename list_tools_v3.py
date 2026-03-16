import os
import sys
import importlib
from pathlib import Path

# Project structure:
# c:\Projects\Atlas\Atlas_v2\
#   core\
#   agent_skills\

atlas_v2_path = r"c:\Projects\Atlas\Atlas_v2"
sys.path.insert(0, atlas_v2_path)

def list_all_axis_tools():
    skills_dir = Path(atlas_v2_path) / "agent_skills"
    
    SKILL_CATEGORIES = {
        "file_master": "Files",
        "terminal_operator": "System",
        "vision_eye": "Media",
        "audio_interface": "Media",
        "diagnostics": "System",
        "memory_manager": "Memory",
        "web_research": "Web",
        "mcp_hub": "System",
        "os_control": "System",
        "telegram_bridge": "System",
        "code_intelligence": "Memory",
        "skill_factory": "System",
        "database_master": "Files"
    }

    print("# AXIS Agent Skills and Tools Comprehensive Report\n")

    for skill_folder in sorted(skills_dir.iterdir()):
        if skill_folder.is_dir() and (skill_folder / "manifest.py").exists():
            category = SKILL_CATEGORIES.get(skill_folder.name, "Other")
            print(f"## Skill: `{skill_folder.name}` (Category: {category})")
            
            try:
                # In this setup, we import as 'agent_skills.name.manifest'
                # because we added Atlas_v2 to sys.path
                module_path = f"agent_skills.{skill_folder.name}.manifest"
                module = importlib.import_module(module_path)
                
                if hasattr(module, "EXPORTED_TOOLS"):
                    for tool in module.EXPORTED_TOOLS:
                        name = getattr(tool, '__name__', str(tool))
                        doc = (getattr(tool, '__doc__', '') or 'No description.').strip()
                        doc_summary = doc.split('\n')[0]
                        print(f"- **{name}**: {doc_summary}")
                else:
                    print("- *No EXPORTED_TOOLS found in manifest.*")
            except Exception as e:
                print(f"- *Error loading manifest: {str(e)}*")
            print("\n")

if __name__ == "__main__":
    list_all_axis_tools()
