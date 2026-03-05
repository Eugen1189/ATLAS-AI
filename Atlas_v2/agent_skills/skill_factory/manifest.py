from core.validator import validate_skill_tool
from core.i18n import lang
import os
from pathlib import Path

def create_skill_skeleton(skill_name: str) -> str:
    """
    Creates the directory and files for a new skill.
    
    Args:
        skill_name: Name of the new skill.
    """
    project_root = Path(__file__).parent.parent.parent
    skill_dir = project_root / "agent_skills" / skill_name
    test_dir = skill_dir / "tests"
    
    os.makedirs(skill_dir, exist_ok=True)
    os.makedirs(test_dir, exist_ok=True)
    
    # Create manifest.py
    manifest_path = skill_dir / "manifest.py"
    if not manifest_path.exists():
        with open(manifest_path, "w", encoding="utf-8") as f:
            f.write(f'from core.i18n import lang\n\ndef my_tool():\n    """Description."""\n    return "Hello"\n\nEXPORTED_TOOLS = [my_tool]\n')
            
    # Create test_logic.py
    test_path = test_dir / "test_logic.py"
    if not test_path.exists():
        with open(test_path, "w", encoding="utf-8") as f:
            f.write(f'import unittest\nfrom agent_skills.{skill_name}.manifest import my_tool\n\nclass Test{skill_name.capitalize()}(unittest.TestCase):\n    def test_basic(self):\n        self.assertEqual(my_tool(), "Hello")\n')

    return f"Skill skeleton for '{skill_name}' created at {skill_dir}. Now you can edit manifest.py and test_logic.py, then run validate_skill_tool."

EXPORTED_TOOLS = [create_skill_skeleton, validate_skill_tool]
