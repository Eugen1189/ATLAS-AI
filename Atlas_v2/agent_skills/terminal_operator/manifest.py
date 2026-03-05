import subprocess
import os
from core.i18n import lang
from core.logger import time_it

@time_it
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
    from core.validator import SecurityValidator
    from core.logger import logger
    import time

    logger.info("terminal.cmd_exec", command=command)

    if not SecurityValidator.is_safe_command(command):
        print(lang.get("terminal.dangerous_command_waiting", cmd=command))
        os.environ["AXIS_CONFIRM"] = "FALSE"
        
        # Explain and wait for confirmation (Thumbs Up or telegram logic)
        confirmed = False
        start_time = time.time()
        while time.time() - start_time < 15:
            if os.environ.get("AXIS_CONFIRM") == "TRUE":
                confirmed = True
                break
            time.sleep(0.5)
            
        if not confirmed:
            os.environ["AXIS_CONFIRM"] = "FALSE"
            return lang.get("dangerous_command", command=command) + " (Not confirmed)"
            
        os.environ["AXIS_CONFIRM"] = "FALSE"
        print("✅ Command Confirmed.")

    # Optional print for CLI UI if you want, using correct kwarg `cmd`
    print(lang.get("terminal.executing", cmd=command))
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
            logger.info("terminal.cmd_success", status=result.returncode)
            return lang.get("terminal.success", output=output if output else lang.get("terminal.no_output"))
        else:
            logger.warning("terminal.cmd_failed", status=result.returncode, error=error)
            return lang.get("terminal.failed", code=result.returncode, error=error, output=output)
            
    except Exception as e:
        logger.error("terminal.crit_error", error=str(e))
        return lang.get("terminal.crit_error", error=e)

# Export tool
EXPORTED_TOOLS = [execute_command]