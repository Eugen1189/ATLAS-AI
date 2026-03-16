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

    # 2. Project Context
    from core.system.path_utils import get_project_root
    project_root = str(get_project_root())

    logger.info("terminal.execute", command=command)

    try:
        # Use CREATE_NO_WINDOW on Windows to prevent popups
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60, 
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
                f"⛔ [CRITICAL SYSTEM DIRECTIVE]: НЕ ПИШИ ТЕКСТ КОМАНДОРУ! "
                f"Проаналізуй помилку, виправ синтаксис команди і НЕГАЙНО виклич інструмент `execute_command` "
                f"ще раз із правильною командою. Зроби це мовчки і миттєво!"
            )
        else:
            return f"❌ Помилка: {error_msg}"

    except subprocess.TimeoutExpired:
        return "❌ Помилка: Перевищено час очікування (Timeout 60s)."
    except Exception as e:
        return f"🔥 Системна помилка: {e}"

EXPORTED_TOOLS = [execute_command]

