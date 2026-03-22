import subprocess
import os
import tempfile
from core.logger import logger
from core.skills.wrapper import agent_tool

from core.security.guard import SecurityGuard

@agent_tool
def execute_command(command: str, auto_fix: bool = True, **kwargs) -> str:
    """Executes any command in the Windows terminal (cmd/powershell). Returns output."""
    
    # 1. Global Security Firewall Check
    if not SecurityGuard.is_safe_command(command):
        return f"🚨 [SECURITY REJECTED]: Дія заблокована Фаєрволом AXIS. Команда '{command}' визнана небезпечною."

    # 2. Project Context (v4.1.0 Context-Aware)
    from core.system.path_utils import get_project_root
    # Prioritize the workspace injected by the orchestrator
    ws = kwargs.get("current_workspace")
    project_root = str(ws if ws else get_project_root())

    logger.info("terminal.execute", command=command, cwd=project_root)

    try:
        # 3. Terminal Execution Context (v4.1.0 PowerShell-First)
        startupinfo = None
        current_cmd = command
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            # Wrap in PowerShell to enable cmdlets and better escaping
            escaped_command = command.replace("\"", "`\"")
            current_cmd = f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{escaped_command}"'

        result = subprocess.run(
            current_cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=120, 
            cwd=project_root,
            startupinfo=startupinfo,
            encoding='utf-8', 
            errors='replace'
        )
        
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Якщо все пройшло добре
        if result.returncode == 0 and not any(err in stderr.lower() for err in ["error", "не является внутренней", "is not recognized"]):
            return f"✅ Успіх:\n{stdout}" if stdout else "✅ Виконано успішно."

        # Якщо сталася помилка
        error_msg = stderr if stderr else stdout
        logger.warning("terminal.error", error=error_msg)

        # --- МАГІЯ АВТОНОМНОГО ДЕБАГГІНГУ (Prevention of LLM Deadlock) ---
        if auto_fix:
            logger.info("terminal.self_correction", status="sending directive")
            return (

                f"❌ КОМАНДА ВПАЛА З ПОМИЛКОЮ:\n{error_msg}\n\n"
                f"📍 [CWD]: {project_root}\n"
                f"⛔ [CRITICAL SYSTEM DIRECTIVE]: Проаналізуй помилку, врахуй поточний шлях і виправ синтаксис (або перейди в папку проекту через 'switch_workspace'). НЕ ПИШИ ТЕКСТ КОМАНДОРУ! Зроби це мовчки і миттєво!"
            )
        else:
            return f"❌ Помилка: {error_msg}"

    except subprocess.TimeoutExpired:
        return "❌ Помилка: Перевищено час очікування (Timeout 60s)."
    except Exception as e:
        return f"🔥 Системна помилка: {e}"

EXPORTED_TOOLS = [execute_command]

