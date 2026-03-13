import os
from pathlib import Path
from core.skills.wrapper import agent_tool
from core.validator import SkillValidator
from core.logger import logger

@agent_tool
def generate_skill_scaffold(name: str, description: str, **kwargs) -> str:
    """
    Creates a new AXIS skill scaffold (v2.8.6).
    Generates manifest.py and a basic test file in a proper structure.
    """
    # orchestrator.py sets CWD to project root (e.g. C:\Projects\Atlas)
    # Skills are in Atlas_v2/agent_skills
    project_root = Path(os.getcwd())
    skill_dir = project_root / "Atlas_v2" / "agent_skills" / name
    test_dir = skill_dir / "tests"
    
    if skill_dir.exists():
        return f"❌ [ERROR]: Skill '{name}' already exists at {skill_dir}."
    
    try:
        os.makedirs(test_dir, exist_ok=True)
        
        # 1. Create manifest.py
        manifest_content = f'''import os
from core.skills.wrapper import agent_tool

# Skill: {name}
# Description: {description}

@agent_tool
def example_tool(param: str, **kwargs) -> str:
    """
    Example tool for {name}.
    """
    return f"Tool {name} executed with param: {{param}}"

EXPORTED_TOOLS = [example_tool]
'''
        with open(skill_dir / "manifest.py", "w", encoding="utf-8") as f:
            f.write(manifest_content)
            
        # 2. Create example test
        test_content = f'''import pytest
from agent_skills.{name}.manifest import example_tool

def test_example_tool():
    result = example_tool(param="test")
    assert "test" in result
'''
        with open(test_dir / f"test_{name}.py", "w", encoding="utf-8") as f:
            f.write(test_content)
            
        return f"✅ [SUCCESS]: Skill '{name}' scaffold created at {skill_dir}. \n" \
               "1. Edit manifest.py to add logic.\n" \
               "2. Run 'verify_skill' to test.\n" \
               "3. Use 'hot_reload_skills' to activate."
        
    except Exception as e:
        return f"❌ [ERROR]: Failed to create skill scaffold: {e}"

@agent_tool
def verify_skill(name: str, **kwargs) -> str:
    """
    Runs pytest for the specified skill. 
    If tests fail, AXIS can use 'Healer' logic to propose a fix.
    """
    result = SkillValidator.run_tests(name)
    if result["success"]:
        return f"✅ [TESTS PASSED]: Skill '{name}' is valid.\n\n{result['output']}"
    else:
        # Prompt model to look for fixes
        return f"❌ [TESTS FAILED]: Skill '{name}' has errors.\n\n[ERROR]:\n{result['error']}\n\n[OUTPUT]:\n{result['output']}\n\n" \
               "💡 TIP: Use 'read_file' to check the code and 'Healer' to find a fix."

EXPORTED_TOOLS = [generate_skill_scaffold, verify_skill]
