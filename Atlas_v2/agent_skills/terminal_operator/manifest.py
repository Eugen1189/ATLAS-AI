import subprocess
import os
import time
import tempfile
import re
import json
from core.i18n import lang
from core.logger import time_it, logger
from core.skills.wrapper import agent_tool

# --- SECURITY FIREWALL ---
DANGEROUS_COMMANDS = [
    r"rm\s+-rf\s+/", r"format\s+", r"del\s+.*system32", r"rd\s+/s",
    r"mkfs", r"dd\s+if=", r"shutdown", r"reboot", r"\.exe"
]

def _check_safety(command: str) -> str | None:
    """Checks if the command is safe and returns the matched danger pattern if not."""
    cmd_lower = command.lower()
    for pattern in DANGEROUS_COMMANDS:
        if re.search(pattern, cmd_lower):
            return pattern
    return None

@agent_tool
def execute_command(command: str, **kwargs) -> str:
    """
    Виконує команди в PowerShell/CMD. ВИКОРИСТОВУЙ ЦЕ для встановлення пакетів (pip, npm), 
    перевірки мережі (ping), роботи з git або системними утилітами.
    """
    # 1. Firewall Check
    forbidden = _check_safety(command)
    if forbidden:
        return json.dumps({
            "status": "success",
            "content": f"Дія заблокована Фаєрволом AXIS. Команда містила заборонений паттерн: '{forbidden}'.",
            "SYSTEM_INSTRUCTION": "Фаєрвол успішно спрацював. Це очікувана поведінка захисту. Тобі НЕ потрібно панікувати, робити діагностику чи вмикати алерти. Просто поясни користувачу, що команда була заблокована з міркувань безпеки."
        }, ensure_ascii=False)

    # 2. Project Context
    # Go up 2 levels from Atlas_v2/agent_skills/terminal_operator/manifest.py
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    logger.info(f"Terminal: Executing '{command}' in {project_root}")

    try:
        # Use CREATE_NO_WINDOW on Windows to prevent popups
        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        process = subprocess.Popen(
            command, 
            shell=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            cwd=project_root,
            startupinfo=startupinfo
        )
        
        try:
            stdout, stderr = process.communicate(timeout=60)
            status = process.returncode
        except subprocess.TimeoutExpired:
            process.kill()
            stdout, stderr = process.communicate()
            return f"⏰ [TIMEOUT]: Команда '{command}' була припинена після 60с.\nЧастковий вивід: {stdout}"

        output, error = stdout.strip(), stderr.strip()
        
        result_msg = []
        if output: result_msg.append(f"STDOUT:\n{output}")
        if error: result_msg.append(f"STDERR:\n{error}")
        
        if status == 0:
            return f"🚀 [SUCCESS]:\n" + "\n".join(result_msg) if result_msg else "Done."
        return f"❌ [ERROR {status}]:\n" + "\n".join(result_msg)
        
    except Exception as e:
        return f"🔥 [CRITICAL ERROR]: {str(e)}"

@agent_tool
def run_batch_script(commands: list, **kwargs) -> str:
    """Executes a list of commands as a temporary .bat script for complex tasks."""
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    with tempfile.NamedTemporaryFile(suffix=".bat", delete=False, mode="w") as f:
        f.write("@echo off\n" + "\n".join(commands))
        script_path = f.name
    
    try:
        res = execute_command(f'call "{script_path}"')
        os.remove(script_path)
        return f"📜 [BATCH EXECUTION DONE]:\n{res}"
    except Exception as e: return f"Script Error: {e}"

@agent_tool
def get_system_uptime(**kwargs) -> str:
    """Quick diagnostic: returns system boot time via CMD."""
    try:
        output = subprocess.check_output("systeminfo | find \"System Boot Time\"", shell=True, text=True)
        return output.strip()
    except Exception: return "Uptime unknown."

EXPORTED_TOOLS = [execute_command, run_batch_script, get_system_uptime]

