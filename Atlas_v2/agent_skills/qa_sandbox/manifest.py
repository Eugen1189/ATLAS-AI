import subprocess
import os
from core.logger import logger
from core.skills.wrapper import agent_tool

@agent_tool
def run_qa_tests(path: str, **kwargs) -> str:
    """
    [VECTOR 2: QA SANDBOX]
    Runs pytest on the specified file or directory to validate code health.
    Ensures that patches didn't break existing functionality.
    """
    logger.info("qa.running_tests", path=path)
    
    if not os.path.exists(path):
        return f"❌ [QA]: File or directory not found: {path}"
        
    try:
        # Run pytest
        cmd = [os.path.join(os.getcwd(), "venv", "Scripts", "pytest"), path]
        if not os.path.exists(cmd[0]):
             cmd = ["pytest", path] # Fallback to system pytest
             
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        output = result.stdout.strip()
        errors = result.stderr.strip()
        
        if result.returncode == 0:
            return f"✅ [QA SUCCESS]: All tests passed in '{path}'. Code is verified.\n\nOutput:\n{output}"
        else:
            return f"❌ [QA FAILED]: Tests failed in '{path}'.\n\nOutput:\n{output}\nError:\n{errors}"
            
    except Exception as e:
        logger.error("qa.test_failed", error=str(e))
        return f"❌ [QA ERROR]: Failed to run tests: {str(e)}"

EXPORTED_TOOLS = [run_qa_tests]
