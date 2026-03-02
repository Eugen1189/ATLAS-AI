"""
Shell Executor - універсальний виконавець системних команд

Реалізує "Метод Clawdbot":
- Генерує PowerShell/Bash скрипти через LLM
- Виконує команди через subprocess
- Безпечне виконання з перевірками
"""

import subprocess
import platform
import os
from typing import Tuple, Optional

# Імпорт CommandCleaner (з обробкою помилок)
try:
    from .command_cleaner import CommandCleaner
    HAS_CLEANER = True
except ImportError:
    # Fallback якщо модуль не знайдено
    HAS_CLEANER = False
    class CommandCleaner:
        @staticmethod
        def clean(cmd): return cmd.strip()
        @staticmethod
        def extract_first_command(cmd): return cmd.strip()


class ShellExecutor:
    """
    Універсальний виконавець системних команд.
    
    Підтримує:
    - Windows PowerShell
    - Linux/Mac Bash
    """
    
    def __init__(self):
        self.os_type = platform.system()
        # Ініціалізуємо cleaner для очищення команд
        if HAS_CLEANER:
            self.cleaner = CommandCleaner()
        else:
            self.cleaner = None
        print(f"✅ [SHELL EXECUTOR] Ініціалізовано для {self.os_type}")
    
    def execute(self, command: str, shell_type: Optional[str] = None) -> Tuple[bool, str]:
        """
        Виконує команду з автоматичним визначенням кодування.
        
        🔥 FIX ENCODING: Правильна обробка кодування для Windows (cp866, cp1251, utf-8, mbcs)
        
        Args:
            command: Команда для виконання (PowerShell або Bash)
            shell_type: Тип shell ('powershell', 'bash', None=auto) - залишено для сумісності
            
        Returns:
            Tuple (success: bool, output: str)
        """
        # 1. Очищення
        if self.cleaner:
            command = self.cleaner.clean(command)
            command = self.cleaner.extract_first_command(command)
        else:
            command = command.strip()
        
        if not command or not command.strip():
            return False, "Порожня команда"
            
        print(f"⚡ [SHELL] Executing: {command[:100]}...")
        
        try:
            # Використовуємо Popen для підтримки pipe (|) та правильного кодування
            if self.os_type == "Windows":
                process = subprocess.Popen(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,  # Читаємо байти, щоб декодувати вручну
                    shell=False  # Popen з списком аргументів безпечніше
                )
            elif self.os_type in ["Linux", "Darwin"]:  # Darwin = Mac
                process = subprocess.Popen(
                    ["bash", "-c", command],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=False,  # Читаємо байти, щоб декодувати вручну
                    shell=False
                )
            else:
                return False, f"Непідтримувана ОС: {self.os_type}"
            
            try:
                stdout_bytes, stderr_bytes = process.communicate(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                return False, "Таймаут обробки команди (>30.0с)"

            # 🔥 FIX ENCODING: Пробуємо різні кодування для Windows
            def decode_output(data_bytes):
                if not data_bytes:
                    return ""
                # Для Windows пробуємо різні кодування
                if self.os_type == "Windows":
                    for encoding in ['cp866', 'cp1251', 'utf-8', 'mbcs']:
                        try:
                            return data_bytes.decode(encoding).strip()
                        except UnicodeDecodeError:
                            continue
                # Для Linux/Mac використовуємо UTF-8
                try:
                    return data_bytes.decode('utf-8').strip()
                except UnicodeDecodeError:
                    pass
                # Fallback: ігноруємо помилки
                return data_bytes.decode('utf-8', errors='ignore').strip()

            stdout_str = decode_output(stdout_bytes)
            stderr_str = decode_output(stderr_bytes)

            if process.returncode == 0:
                return True, stdout_str if stdout_str else "Виконано успішно (без виводу)"
            else:
                # returncode != 0 завжди означає помилку (звіт LegacyLens Step 6)
                err_msg = stderr_str.strip() if stderr_str else f"Exit code {process.returncode}"
                return False, f"Помилка: {err_msg}"

        except Exception as e:
            return False, f"Критична помилка запуску: {str(e)}"

    def validate_command(self, command: str) -> Tuple[bool, str]:
        """
        Перевіряє команду на безпеку перед виконанням.
        
        Args:
            command: Команда для перевірки
            
        Returns:
            Tuple (is_safe: bool, reason: str)
        """
        if not command:
            return False, "Порожня команда"
        
        command_lower = command.lower()
        
        # ⚠️ НЕБЕЗПЕЧНІ КОМАНДИ (блокуються)
        dangerous_patterns = [
            "format",  # Форматування диска
            "del /f /s /q",  # Видалення файлів без підтвердження
            "rm -rf /",  # Видалення кореневого каталогу
            "shutdown",  # Вимикання системи
            "restart",  # Перезавантаження
            "reg delete",  # Видалення реєстру
            "bcdedit",  # Зміна завантаження
            "diskpart",  # Робота з дисками
        ]
        
        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return False, f"Команда містить небезпечну операцію: {pattern}"
        
        # ✅ БЕЗПЕЧНІ ОПЕРАЦІЇ (дозволені)
        safe_operations = [
            "get-childitem", "get-location", "test-path",  # PowerShell читання
            "ls", "cat", "pwd", "find",  # Bash читання
            "move-item", "copy-item", "new-item",  # PowerShell запис (з обережністю)
            "mv", "cp", "mkdir",  # Bash запис (з обережністю)
        ]
        
        # Якщо команда містить операції запису - потребує підтвердження
        write_operations = ["move-item", "copy-item", "remove-item", "mv", "cp", "rm"]
        has_write = any(op in command_lower for op in write_operations)
        
        # 🚀 ЕТАП 3: Операції керування процесами також потребують підтвердження
        process_control_operations = ["stop-process", "kill", "terminate", "закрий", "убий"]
        has_process_control = any(op in command_lower for op in process_control_operations)
        
        if has_write or has_process_control:
            return True, "Потребує підтвердження (операція запису/керування процесом)"
        
        return True, "Безпечна команда"
    
    def format_command_for_display(self, command: str) -> str:
        """
        Форматує команду для відображення користувачу.
        
        Args:
            command: Команда для форматування
            
        Returns:
            Відформатована команда
        """
        # Обрізаємо довгі команди
        if len(command) > 200:
            return command[:200] + "..."
        return command
