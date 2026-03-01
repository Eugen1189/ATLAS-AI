import subprocess
import os

def execute_command(command: str) -> str:
    """
    Виконує системну команду в терміналі (PowerShell/CMD) та повертає результат (stdout/stderr).
    Використовуй цей інструмент для:
    1. Запуску скриптів (наприклад, 'python test.py').
    2. Встановлення пакетів (наприклад, 'pip install requests').
    3. Роботи з Git ('git status', 'git add .', 'git commit -m "..."').
    4. Перевірки системи ('ping google.com', 'ipconfig', 'dir').
    
    УВАГА: Ніколи не виконуй деструктивні команди (format, del /f /s /q) без прямого дозволу користувача.
    
    Args:
        command: Команда для виконання в терміналі.
    """
    print(f"⚡ [Terminal Operator]: Виконую команду: `{command}`")
    try:
        # Виконуємо команду і перехоплюємо вивід
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            # Працюємо в директорії кореня проекту (піднімаємося на 2 рівні від папки скіла)
            cwd=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        )
        
        output = result.stdout.strip()
        error = result.stderr.strip()
        
        if result.returncode == 0:
            return f"✅ Команда виконана успішно.\nВивід:\n{output if output else 'Без текстового виводу.'}"
        else:
            return f"❌ Команда завершилася з помилкою (Код {result.returncode}).\nПомилка:\n{error}\nЧастковий вивід:\n{output}"
            
    except Exception as e:
        return f"Критична помилка під час виконання команди: {e}"

# Експортуємо інструмент
EXPORTED_TOOLS = [execute_command]