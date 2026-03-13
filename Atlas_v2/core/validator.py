import subprocess
from pathlib import Path
from core.logger import logger
from core.i18n import lang


class SecurityValidator:
    """Validates commands and code for security risks."""

    @staticmethod
    def is_safe_command(command: str) -> bool:
        """Checks if a shell command contains known dangerous patterns."""
        from core.security.guard import SecurityGuard
        return SecurityGuard.is_safe_command(command)

    @staticmethod
    def validate_python_syntax(code: str) -> bool:
        """Checks if Python code is syntactically valid."""
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError as e:
            logger.error("security.syntax_error", error=str(e))
            return False

class SkillValidator:
    """Handles autonomous validation of agent skills via pytest/unittest."""
    
    @staticmethod
    def run_tests(skill_name: str) -> dict:
        """
        Runs tests for a specific skill.
        Expects tests to be located in agent_skills/{skill_name}/tests/
        
        Returns:
            dict: {
                "success": bool,
                "output": str,
                "error": str
            }
        """
        project_root = Path(__file__).parent.parent
        skill_dir = project_root / "agent_skills" / skill_name
        test_dir = skill_dir / "tests"
        
        if not test_dir.exists():
            return {
                "success": False,
                "output": "",
                "error": f"Test directory not found: {test_dir}"
            }
            
        logger.info("system.validating_skill", name=skill_name)
        
        try:
            # Run pytest on the skill's test directory
            # We use subprocess to run pytest in the same environment
            result = subprocess.run(
                ["pytest", str(test_dir), "-v"],
                capture_output=True,
                text=True,
                cwd=str(project_root)
            )
            
            success = result.returncode == 0
            return {
                "success": success,
                "output": result.stdout,
                "error": result.stderr
            }
            
        except Exception as e:
            logger.error("system.validation_error", name=skill_name, error=str(e))
            return {
                "success": False,
                "output": "",
                "error": str(e)
            }

def validate_skill_tool(skill_name: str) -> str:
    """
    AXIS Tool: Validates a skill by running its unit tests.
    Use this after creating or modifying a skill.
    
    Args:
        skill_name: The name of the skill folder (e.g., 'file_master').
    """
    validator = SkillValidator()
    result = validator.run_tests(skill_name)
    
    if result["success"]:
        return lang.get("system.validation_success", name=skill_name) + "\n" + result["output"]
    else:
        return lang.get("system.validation_failed", name=skill_name) + "\n" + result["error"] + "\n" + result["output"]

EXPORTED_TOOLS = [validate_skill_tool]
