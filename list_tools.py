import os
import sys
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

    print("# AXIS Agent Skills and Tools Report\n")

    for skill_folder in sorted(skills_dir.iterdir()):
        if skill_folder.is_dir() and (skill_folder / "manifest.py").exists():
            category = SKILL_CATEGORIES.get(skill_folder.name, "Other")
            print(f"## Skill: `{skill_folder.name}` (Category: {category})")
            
            manifest_path = skill_folder / "manifest.py"
            with open(manifest_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Basic parsing of EXPORTED_TOOLS and docstrings
            # This is a bit rough but should work for a report
            tools = []
            lines = content.split('\n')
            
            # Find EXPORTED_TOOLS line
            exported_line = ""
            for line in reversed(lines):
                if "EXPORTED_TOOLS =" in line:
                    exported_line = line
                    break
            
            if exported_line:
                tool_names = exported_line.split('[')[1].split(']')[0].split(',')
                tool_names = [t.strip() for t in tool_names if t.strip()]
                
                for t_name in tool_names:
                    # Find function definition and docstring
                    docstring = "No description."
                    found_func = False
                    for i, line in enumerate(lines):
                        if f"def {t_name}(" in line:
                            found_func = True
                            # Look for docstring in next few lines
                            for j in range(i+1, min(i+10, len(lines))):
                                if '"""' in lines[j] or "'''" in lines[j]:
                                    doc = lines[j].split('"""')[1] if '"""' in lines[j] else lines[j].split("'''")[1]
                                    if not doc.strip(): # multicline docstring
                                         doc = lines[j+1].strip()
                                    docstring = doc.strip()
                                    break
                            break
                    print(f"- **{t_name}**: {docstring}")
            print("\n")

if __name__ == "__main__":
    list_all_axis_tools()
