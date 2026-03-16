import os
import sys
import importlib
from pathlib import Path

# Add project root to sys.path
project_root = r"c:\Projects\Atlas"
sys.path.insert(0, project_root)

def list_all_axis_tools():
    skills_dir = Path(project_root) / "Atlas_v2" / "agent_skills"
    
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
                module_path = f"Atlas_v2.agent_skills.{skill_folder.name}.manifest"
                module = importlib.import_module(module_path)
                
                if hasattr(module, "EXPORTED_TOOLS"):
                    for tool in module.EXPORTED_TOOLS:
                        name = getattr(tool, '__name__', str(tool))
                        doc = (getattr(tool, '__doc__', '') or 'No description.').strip()
                        # Take only the first line of docstring for summary
                        doc_summary = doc.split('\n')[0]
                        print(f"- **{name}**: {doc_summary}")
                else:
                    print("- *No EXPORTED_TOOLS found in manifest.*")
            except Exception as e:
                print(f"- *Error loading manifest: {str(e)}*")
            print("\n")

if __name__ == "__main__":
    list_all_axis_tools()
