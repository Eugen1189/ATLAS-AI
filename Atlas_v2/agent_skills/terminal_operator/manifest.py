import subprocess
import os
from core.i18n import lang

def execute_command(command: str) -> str:
    """
    Executes a system command in the terminal (PowerShell/CMD) and returns the result (stdout/stderr).
    Use this tool for:
    1. Running scripts (e.g., 'python test.py').
    2. Installing packages (e.g., 'pip install requests').
    3. Working with Git ('git status', 'git add .', 'git commit -m "..."').
    4. System inquiries ('ping google.com', 'ipconfig', 'dir').
    
    WARNING: Never execute destructive commands (format, del /f /s /q) without the direct permission of the user.
    
    Args:
        command: Command to execute in the terminal.
    """
    print(lang.get("terminal.executing", command=command))
    try:
        # Execute the command and capture output
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            # Work in the project root directory (go up 2 levels from the skill folder)
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return lang.get("terminal.success", output=output if output else lang.get("terminal.no_output"))
        else:
            return lang.get("terminal.failed", code=result.returncode, error=error, output=output)
            
    except Exception as e:
        return lang.get("terminal.crit_error", error=e)

# Export tool
EXPORTED_TOOLS = [execute_command]