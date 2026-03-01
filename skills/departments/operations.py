"""
Operations Department - об'єднаний департамент

Об'єднує функціонал:
- System Department (статус, музика, очищення)
- Web Department (відкриття сайтів, YouTube Music)
- Launcher Department (запуск програм)

Пріоритет: 4
"""

import sys
import webbrowser
import re
from pathlib import Path
from typing import Optional

# Додаємо батьківську директорію для імпорту
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import config
from .base import Department
from skills.launcher import Launcher
from skills.system_ops import clean_capcut_cache, empty_recycle_bin
from skills.shell_executor import ShellExecutor
from skills.scenario_manager import ScenarioManager
from skills.system_navigator import SystemNavigator  # New Native Navigator
try:
    from skills.music import play_music, stop_music
except ImportError:
    def play_music():
        return "Модуль music.py недоступний"
    def stop_music():
        pass


from core.visual_bridge import get_visual_bridge


class OperationsDepartment(Department):
    """
    Об'єднаний департамент для системних операцій, запуску програм та веб-ресурсів.
    
    Пріоритет: 4
    """
    
    def __init__(self):
        """Ініціалізація Operations Department"""
        super().__init__("Operations", priority=4)
        
        # Тригери (об'єднані з усіх трьох департаментів)
        self.triggers = [
            # System тригери
            "музика", "музику", "включи музику", "зупини музику",
            "кіно", "фільм",
            "очисти кеш", "очисти кошик", "очисти",
            "як ти",

            # Web тригери
            "ютуб", "youtube", "гітхаб", "github", "чат", "chatgpt",
            "знайди", "пошукай", "гугл", "пошук",
            "відкрий сайт", "перейди на",
            # Launcher тригери
            "відкрий", "запусти", "відкрити",
            "курсор", "хром", "chrome", "телеграм", "telegram",
            "калькулятор", "блокнот", "notepad",
            # 🤖 Automation тригери (Руки для ATLAS)
            "клікни", "натисни", "введи текст", "введи", "напиши",
            "активуй вікно", "переключи вікно", "скрол", "прокрути",
            "перемісти мишу", "позиція миші", "гарячі клавіші", "hotkey",
            "покажи робочий стіл", "згорни все", "workspace", "робочий простір",
            "аудит", "audit", "screen audit",
            # 🧠 Self-Awareness
            "онбординг", "onboarding", "аналіз коду", "analyze code",
            "roadmap", "план розвитку", "архітектура", "structure"
        ]
        
        # Ініціалізація компонентів
        self.launcher = Launcher()

        self.shell_executor = ShellExecutor()  # 🆕 Shell Executor (Метод Clawdbot)
        self.scenario_manager = ScenarioManager()  # 🎬 Scenario Manager (ЕТАП 4)
        self.navigator = SystemNavigator()  # 🤖 System Navigator (Native Hands)
        
        self.preset_commands = {}
        
        # Стан для підтвердження команд
        self.pending_command = None
        self.pending_context = None
        self.model = None  # Буде встановлено через set_model()
        
        # Стан для підтвердження команд
        self.pending_command = None
        self.pending_context = None
        self.model = None  # Буде встановлено через set_model()
        
        # Словник сайтів (з Web Department)
        self.sites = {
            "ютуб": "https://www.youtube.com",
            "youtube": "https://www.youtube.com",
            "ютуб музика": "https://music.youtube.com",
            "youtube music": "https://music.youtube.com",
            "гітхаб": "https://github.com",
            "github": "https://github.com",
            "чат": "https://chat.openai.com",
            "chatgpt": "https://chat.openai.com",
            "музика": "https://music.youtube.com",  # За замовчуванням YouTube Music
            "кіно": "https://www.youtube.com/results?search_query=фільм",
            "фільм": "https://www.youtube.com/results?search_query=фільм",
        }
        
        # Мапа програм (з Launcher Department)
        self.apps_map = {
            "курсор": "cursor",
            "cursor": "cursor",
            "хром": "chrome",
            "chrome": "chrome",
            "телеграм": "telegram",
            "telegram": "telegram",
            "калькулятор": "калькулятор",
            "calc": "калькулятор",
            "блокнот": "блокнот",
            "notepad": "блокнот"
        }
        
        # 📚 Словник стандартних програм (які не знаходять автоматично)
        self.common_apps = {
            "калькулятор": "calc",
            "calc":        "calc",
            "блокнот":     "notepad",
            "notepad":     "notepad",
            "cursor":      "cursor",  # Команда 'cursor' є в PATH
            "ide":         "cursor",
            "редактор":    "cursor",
            "код":         "cursor",
            "telegram":    "Telegram",
            "телеграм":    str(config.TELEGRAM_PATH),  # з config.py — без хардкоду
            "paint":       "mspaint",
            "cmd":         "start cmd",
            "powershell":  "start powershell"
        }
        
        # Аліас для reflex_commands (для сумісності)
        self.reflex_commands = self.preset_commands
        
        print("✅ [OPERATIONS DEPT] Компоненти ініціалізовано")
    
    def open_app_wrapper(self, query: str, context, app_name: str) -> str:
        """Обгортка для запуску програм через Command Registry"""
        # Спершу перевіряємо common_apps
        for name, run_cmd in self.common_apps.items():
            if name.lower() == app_name.lower():
                command = f"Start-Process '{run_cmd}'"
                if run_cmd == "start cmd": command = "Start-Process cmd"
                elif run_cmd == "start powershell": command = "Start-Process powershell"
                
                try:
                    success, output = self.shell_executor.execute(command)
                    if success:
                        if context:
                            context.log_action(f"Operations: Запущено {app_name}")
                        return f"Запускаю {app_name}..."
                    else:
                        return f"Помилка запуску {app_name}: {output}"
                except Exception as e:
                    return f"Помилка запуску {app_name}: {e}"
        
        # Якщо не знайшли в common - пробуємо Launcher
        try:
             get_visual_bridge().send_system_event("app_launch", app_name)
        except: pass
        return self.launcher.open_app(app_name)

    def _handle_reflex_command(self, query: str, context, reflex_key: str) -> str:
        """Обгортка для рефлексів через Command Registry"""
        # Перевіряємо, чи є скрипт для цього ключа
        script = self.reflex_commands.get(reflex_key)
        if script:
            success, output = self.shell_executor.execute(script)
            if success:
                if context:
                    context.log_action(f"Operations: Рефлекс '{reflex_key}' виконано")
                return output.strip() if output else "Готово"
            else:
                return f"Помилка рефлексу: {output}"
        return "Невідомий рефлекс."

    def stop_music_wrapper(self, query: str, context) -> str:
        """Обгортка для зупинки музики"""
        stop_music()
        if context:
            context.log_action("Operations: Зупинено музику")
        return "Музику зупинено."

    def _take_screenshot_wrapper(self, query: str, context) -> str:
        """Обгортка для створення скріншоту"""
        path = self.navigator.take_screenshot()
        if path:
            if context:
                context.log_action(f"Operations: Зроблено скріншот: {path}")
            return f"Скріншот збережено: {path}"
        return "Помилка створення скріншота"

    def set_model(self, model):
        """Встановлює Gemini модель для генерації команд"""
        self.model = model
    
    def can_handle(self, query: str) -> bool:
        """
        Приймає запит, якщо це проста технічна команда (запуск, закриття, системна інфо).
        """
        query_lower = query.lower()
        words = query_lower.split()

        # Список конкретних тригерів
        triggers = [
            "запусти", "відкрий", "убий", "kill", "close", "start",
            "файли", "папк", "створи папку", "видали", "перемісти", "copy",
            "адреса", "скрол", "клік", "натисни",
            "гучність", "звук", "вимкни пк", "перезавантаж", "очисти кошик",
            "пауза", "відтворення", "play", "pause", "media",
            "робочий стіл", "desktop", "вікно", "window", "архітектура", "аудит", "audit"
        ]

        # Логіка:
        # 1. Запит має бути коротким (до 10 слів). 
        # 2. Запит має містити тригер.
        if len(words) < 10:
            for t in triggers:
                if t in query_lower:
                    return True
        
        return False
    
    def handle(self, query: str, context=None) -> str:
        """
        Обробляє запит Operations Department з правильним порядком перевірок.
        
        Порядок пріоритетів:
        1. Підтвердження команд
        2. Сценарії (Work Mode, Gaming Mode)
        3. МУЗИКА (локальна) - перед іншими перевірками
        4. Керування процесами (Kill > Run)
        5. Рефлекси (Temp, CPU, Ping)
        6. Запуск програм (Launcher)
        7. Автоматизація (Automation)
        8. Fallback to Shell (LLM)
        """
        query_lower = query.lower()

        # 0. ATOMIC OPERATIONS ORCHESTRATOR
        # Перевіряємо на наявність послідовності дій
        from skills.command_registry import get_registry
        registry = get_registry()
        steps = registry.split_sequence(query)
        
        if len(steps) > 1:
            import time
            results = []
            print(f"🔄 [OPERATIONS] Detected atomic sequence: {steps}")
            
            for i, step in enumerate(steps):
                # Log intent
                if context: context.log_action(f"Step {i+1}: {step}")
                
                # Візуальний сигнал для кожного кроку
                try: get_visual_bridge().send_system_event("sequence_step", i+1)
                except: pass
                
                # Execute recursively
                res = self.handle(step, context)
                results.append(f"Step {i+1}: {res}")
                
                # Removed fixed delay for performance
                # if i < len(steps) - 1:
                #     time.sleep(1.5) 
            
            return "\n".join(results)



        # === 1. ПІДТВЕРДЖЕННЯ (Найвищий пріоритет) ===
        # Якщо користувач каже "так" і у нас висить команда
        if self.pending_command and query_lower in ["так", "yes", "підтверджую", "виконай", "давай"]:
            return self.confirm_command("yes")
        if self.pending_command and query_lower in ["ні", "no", "скасуй"]:
            return self.confirm_command("no")

        # === 2. СЦЕНАРІЇ (Work Mode, Gaming Mode) ===
        # Перевіряємо за назвою, якщо це прямий виклик
        if self.scenario_manager.is_scenario_request(query):
            scenario_result = self.scenario_manager.execute_scenario(query, self.shell_executor)
            if scenario_result: 
                if context:
                    context.log_action(f"Operations: Виконано сценарій")
                return scenario_result

        # === 3. МУЗИКА (локальна) - ПЕРЕД іншими перевірками ===
        # Перевіряємо ДО перевірки на "зупини процес", щоб не перехопити "зупини музику"
        if "зупини музику" in query_lower or "стоп музика" in query_lower:
            stop_music()
            try: get_visual_bridge().send_system_event("music_stop")
            except: pass
            if context:
                context.log_action("Operations: Зупинено музику")
            return "Музику зупинено."

        # Пауза/відтворення (глобальна медіа-клавіша, для зон Vision)
        if any(t in query_lower for t in ["пауза відтворення", "play pause", "toggle media", "пауза музики", "відтвори пауза", "toggle_media"]):
            try:
                import pyautogui
                pyautogui.press("playpause")
                if context:
                    context.log_action("Operations: Пауза/відтворення")
                return "Пауза/відтворення."
            except Exception as e:
                return f"Помилка: {e}"
        
        if any(t in query_lower for t in ["включи локальну музику"]):
            result = play_music()
            if context:
                context.log_action("Operations: Запущено локальну музику")
            return result

        # --- GESTURE ACTIONS ---
        if any(t in query_lower for t in ["покажи робочий стіл", "згорни все", "show_desktop"]):
            try:
                import pyautogui
                pyautogui.hotkey('win', 'd')
                if context: context.log_action("Operations: Show Desktop (Win+D)")
                return "Desktop shown."
            except Exception as e: return f"Error: {e}"

        if any(t in query_lower for t in ["переключи вікно", "switch_window"]):
            try:
                import pyautogui
                pyautogui.hotkey('alt', 'tab')
                if context: context.log_action("Operations: Switch Window (Alt+Tab)")
                return "Window switched."
            except Exception as e: return f"Error: {e}"

        # === 4. КЕРУВАННЯ ПРОЦЕСАМИ (Kill > Run) ===
        # Щоб "Убий Chrome" не запускало Chrome
        # Перевіряємо тільки специфічні команди для процесів (не "зупини музику")
        kill_keywords = ["убий", "kill", "закрий процес"]
        # "зупини" тільки якщо це стосується процесів, а не музики
        if any(w in query_lower for w in kill_keywords) or ("зупини" in query_lower and "процес" in query_lower):
            # Примусово йдемо в Shell Executor для Kill команд
            return self._handle_shell_command(query, context)

        # Рефлекси видалено - вони тепер у окремих скілах або через LLM
        pass

        # === 5. ЗАПУСК ПРОГРАМ (Launcher) ===
        if any(w in query_lower for w in ["запусти", "відкрий", "start", "open", "відкрити"]):
            # Спершу перевіряємо common_apps
            for app_name, run_cmd in self.common_apps.items():
                if app_name in query_lower:
                    try:
                        # Запускаємо безпосередньо через PowerShell
                        if run_cmd in ["calc", "notepad", "mspaint", "cmd", "powershell", "cursor"]:
                            # Системні команди (в PATH)
                            command = f"Start-Process '{run_cmd}'"
                        elif run_cmd == "start cmd":
                            # Спеціальна обробка для cmd
                            command = "Start-Process cmd"
                        elif run_cmd == "start powershell":
                            # Спеціальна обробка для powershell
                            command = "Start-Process powershell"
                        else:
                            # Повний шлях до exe або назва програми
                            command = f"Start-Process '{run_cmd}'"
                        success, output = self.shell_executor.execute(command)
                        if success:
                            if context:
                                context.log_action(f"Operations: Запущено {app_name}")
                            return f"Запускаю {app_name}..."
                        else:
                            return f"Помилка запуску {app_name}: {output}"
                    except Exception as e:
                        return f"Помилка запуску {app_name}: {e}"
            
            # Якщо не знайшли в common - пробуємо Launcher (пошук exe)
            # Витягуємо назву програми
            app_name = query_lower.replace("запусти", "").replace("відкрий", "").replace("start", "").replace("open", "").strip()
            # Перевіряємо apps_map
            for app_key, app_value in self.apps_map.items():
                if app_key in query_lower:
                    result = self.launcher.open_app(app_value)
                    if context:
                        context.log_action(f"Operations: Запущено {app_value}")
                    return result
            # Якщо не знайшли в apps_map, пробуємо через launcher
            if app_name:
                result = self.launcher.open_app(app_name)
                if context:
                    context.log_action(f"Operations: Запущено {app_name}")
                return result
            return "Програму не знайдено."

        # === 7. АВТОМАТИЗАЦІЯ (Automation) ===
        if any(kw in query_lower for kw in ["клікни", "натисни", "введи", "скрол", "прокрути", "активуй вікно", "переключи вікно", "гарячі клавіші", "hotkey"]):
            return self._handle_automation(query, context)
        
        # === 8. WEB: МУЗИКА (YouTube Music) ===
        if any(t in query_lower for t in ["музика", "музику", "включи музику"]) and "локальну" not in query_lower:
            url = self.sites.get("музика", "https://music.youtube.com")
            webbrowser.open(url)
            if context:
                context.log_action("Operations: Відкрито YouTube Music")
            return "Відкриваю YouTube Music..."
        
        # === 9. WEB: САЙТИ ===
        if any(site in query_lower for site in self.sites.keys()):
            # Знаходимо сайт
            for site_key, site_url in self.sites.items():
                if site_key in query_lower:
                    webbrowser.open(site_url)
                    if context:
                        context.log_action(f"Operations: Відкрито {site_key}")
                    return f"Відкриваю {site_key}..."
            return "Сайт не знайдено."
        
        # === 10. WEB: КІНО/ФІЛЬМИ ===
        if any(t in query_lower for t in ["кіно", "фільм"]):
            url = self.sites.get("кіно", "https://www.youtube.com/results?search_query=фільм")
            webbrowser.open(url)
            if context:
                context.log_action("Operations: Відкрито кіно")
            return "Відкриваю кіно..."
        
        # === 11. WEB: SEARCH (Perplexity) ===
        search_triggers = ["знайди", "пошукай", "гугл", "гуглі", "пошук", "google", "search"]
        if any(t in query_lower for t in search_triggers):
            search_query = query_lower
            noise = ["в гуглі", "в google", "в інтернеті", "в гугл", "знайди", "пошукай", "гугл", "гуглі", "пошук", "google", "search", "про "]
            for n in noise:
                search_query = search_query.replace(n, "").strip()
            
            search_query = search_query.replace("атлас", "").strip().strip(",")
            
            if search_query:
                return self.web_search(search_query)
            else:
                import os
                os.startfile("https://www.perplexity.ai")
                return "Opened Perplexity."
        
        # === 12. SYSTEM: ОЧИЩЕННЯ КЕШУ ===
        if "очисти кеш" in query_lower or "очисти кеш capcut" in query_lower:
            result = clean_capcut_cache()
            if context:
                context.log_action("Operations: Очищено кеш CapCut")
            return result
        
        # === 13. SYSTEM: ОЧИЩЕННЯ КОШИКА ===
        if "очисти кошик" in query_lower or "очисти корзину" in query_lower:
            result = empty_recycle_bin()
            if context:
                context.log_action("Operations: Очищено кошик")
            return result
        
        

        
        # === 16. SELF-AWARENESS: CODE ANALYSIS ===
        if any(t in query_lower for t in ["онбординг", "onboarding", "аналіз коду", "roadmap", "архітектура", "що це за проект"]):
             return self._handle_code_analysis(query, context)

        # === 17. ПЕРЕВІРКА НА РОЗМОВНІ/ФІЛОСОФСЬКІ ЗАПИТИ ===
        # Якщо це розмова, а не команда - повертаємо None для fallback до Brain/Oracle
        conversational_keywords = [
            "як ти думаєш", "що ти думаєш", "твоя думка", "твоя думка про",
            "сенс життя", "що таке", "поясни", "розкажи про",
            "чому", "навіщо", "для чого", "як це працює",
            "що означає", "що таке", "що це", "що воно",
            "філософія", "філософське", "думка", "думаєш"
        ]
        
        # Перевіряємо, чи це розмова (не команда для виконання)
        is_conversational = any(kw in query_lower for kw in conversational_keywords)
        
        # Якщо це питання без системних команд - це розмова
        if is_conversational:
            # Перевіряємо, чи немає системних команд у запиті
            system_action_keywords = [
                "запусти", "відкрий", "створи", "видали", "перемісти", "скопіюй",
                "покажи", "знайди файл", "створи папку", "виконай", "зроби"
            ]
            has_system_action = any(kw in query_lower for kw in system_action_keywords)
            
            if not has_system_action:
                # Це розмова - повертаємо None для fallback до Brain/Oracle
                print("💬 [OPERATIONS] Розмовний запит - передаю до Brain/Oracle")
                return None
        
        # === 17. FALLBACK TO SHELL (LLM) ===
        # Якщо нічого не підійшло - нехай думає Gemini (створення папок, пошук файлів)
        return self._handle_shell_command(query, context)

    def _handle_shell_command(self, query: str, context=None) -> str:
        """
        Генерація скриптів через LLM (Brain).
        Обробляє команди для файлів та інших операцій, які не є простими рефлексами.
        """
        # Перевіряємо спочатку рефлекси (якщо ще не перевірено)
        query_lower = query.lower()
        for key, script in self.preset_commands.items():
            if re.search(rf"\b{re.escape(key)}\b", query_lower):
                print(f"⚡ [OPERATIONS] Спрацював рефлекс для '{key}' - виконую БЕЗ LLM")
                success, output = self.shell_executor.execute(script)
                if success:
                    if context:
                        context.log_action(f"Operations: Рефлекс '{key}' виконано")
                    return output.strip() if output else "Готово"
                else:
                    return f"Помилка рефлексу: {output}"
        
        if not self.model:
            return "Модель не підключена, не можу згенерувати скрипт."

        print(f"🐚 [OPERATIONS] Генерую скрипт для: {query}")
        
        system_instruction = """
        ROLE: Windows PowerShell Expert.
        TASK: Convert user query to PowerShell command.
        RULES:
        1. Output ONLY the code. No markdown, no explanations.
        2. START command with: [Console]::OutputEncoding = [System.Text.Encoding]::UTF8;
        3. CRITICAL: DO NOT use 'Out-String -Encoding'. It crashes on Windows PowerShell 5.1.
        4. For 'list files', use Get-ChildItem and format explicitly.
        5. For 'kill process', use Stop-Process -Force.
        6. For Documents folder, use: $docs = if (Test-Path "$env:USERPROFILE\OneDrive\Documents") { "$env:USERPROFILE\OneDrive\Documents" } else { [Environment]::GetFolderPath("MyDocuments") }
        7. For Desktop, use: $desktop = if (Test-Path "$env:USERPROFILE\OneDrive\Desktop") { "$env:USERPROFILE\OneDrive\Desktop" } else { [Environment]::GetFolderPath("Desktop") }
        8. For file operations, check if paths exist before operations.
        """
        
        try:
            prompt = f"{system_instruction}\nUSER QUERY: {query}\nPOWERSHELL CODE:"
            response = self.model.generate_content(prompt)
            raw_command = response.text.strip()
            
            # Очищення від markdown
            command = raw_command.replace("```powershell", "").replace("```", "").strip()
            
            # Додаткове очищення через CommandCleaner
            try:
                from skills.command_cleaner import CommandCleaner
                command = CommandCleaner.clean(command)
                command = CommandCleaner.extract_first_command(command)
            except ImportError:
                pass
            
            # Видаляємо рядки з поясненнями
            lines = command.split('\n')
            cleaned_lines = []
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                # Пропускаємо рядки з поясненнями
                if any(word in line.lower() for word in ['вітаю', 'привіт', 'для windows', 'for windows', 'команда', 'command', 'output', 'вивід']):
                    continue
                # Пропускаємо markdown блоки
                if line.startswith('```') or line.endswith('```'):
                    continue
                cleaned_lines.append(line)
            
            if cleaned_lines:
                command = ' '.join(cleaned_lines)
            
            print(f"✅ [OPERATIONS] Очищена команда: {command[:100]}...")
            
            # Перевірка безпеки
            is_safe, msg = self.shell_executor.validate_command(command)
            if not is_safe:
                # Зберігаємо для підтвердження
                self.pending_command = command
                self.pending_context = context
                formatted_cmd = self.shell_executor.format_command_for_display(command)
                return f"⚠️ Потрібне підтвердження: {msg}\nКоманда: {formatted_cmd}\nСкажіть 'так' для виконання."
            
            # Перевірка на операції запису/керування процесами (потребують підтвердження)
            write_operations = ["move-item", "copy-item", "remove-item", "new-item", "mv", "cp", "rm"]
            process_control_operations = ["stop-process", "kill", "terminate"]
            command_lower = command.lower()
            needs_confirmation = any(op in command_lower for op in write_operations) or any(op in command_lower for op in process_control_operations)
            
            if needs_confirmation:
                # Зберігаємо команду для підтвердження
                self.pending_command = command
                self.pending_context = context
                formatted_cmd = self.shell_executor.format_command_for_display(command)
                return f"⚠️ Я збираюся виконати операцію запису:\n\n{formatted_cmd}\n\nСкажіть 'так' або 'виконай' для підтвердження, або 'ні' для скасування."
            
            # Виконання
            success, output = self.shell_executor.execute(command)
            if success:
                if context:
                    context.log_action(f"Operations: Виконано команду: {command[:50]}...")
                return output.strip() if output else ""
            else:
                return f"Помилка PowerShell: {output}"
            
        except Exception as e:
            return f"Помилка генерації скрипта: {e}"
    
    def _handle_automation(self, query: str, context=None) -> str:
        """
        Обробляє команди автоматизації UI (Руки для ATLAS).
        Аліас для _handle_automation_command для сумісності.
        """
        return self._handle_automation_command(query, context)
    
    def _handle_automation_command(self, query: str, context=None) -> str:
        """
        Обробляє команди автоматизації UI (Руки для ATLAS).
        
        Args:
            query: Запит користувача
            context: Контекст
            
        Returns:
            Результат виконання
        """
        # Використовуємо новий System Navigator
        query_lower = query.lower()
        
        try:
             # 1. Клік (Visual) - вже має свій handler, але для сумісності з прямим викликом
            if "клікни" in query_lower or "натисни" in query_lower:
                return self.handle_visual_click(query, context)

            # 2. Текст
            if "введи" in query_lower or "напиши" in query_lower:
                return self.handle_type_text(query, context)

            # 3. Клавіші
            if "press" in query_lower or "клавіш" in query_lower:
                 key = query.split()[-1] # Simple extraction
                 return self.navigator.press_key(key)
                 
            return "Команда автоматизації не розпізнана. Спробуйте через реєстр."
        except Exception as e:
            return f"Помилка автоматизації: {e}"

    def handle_visual_click(self, query: str, context, target: str = None) -> str:
        """Handler for visual click command"""
        if not target:
             import re
             match = re.search(r"(на|click|клікни)\s+(?P<target>.+)", query, re.IGNORECASE)
             target = match.group("target") if match else None
        
        if not target: return "Не вказано, на що клікати."
        
        if context: context.log_action(f"Operations: Visual Click '{target}'")
        
        # Call the visual click logic (imported essentially from tools logic or implemented here)
        # Re-using the logic we put in tools_definition is tricky. 
        # Better: Implement High-Level Visual Click HERE using Brain.
        
        screenshot_path = self.navigator.take_screenshot("temp_vision_click.png")
        if not screenshot_path: return "Помилка скріншоту."
        
        if not self.model: return "Модель Brain не підключена."
        
        import PIL.Image
        img = PIL.Image.open(screenshot_path)
        prompt = f"Find bounding box for '{target}'. JSON: [ymin, xmin, ymax, xmax] (0-1000). Return [] if not found."
        
        try:
             response = self.model.generate_content([prompt, img])
             import json, re
             text = response.text.strip()
             match = re.search(r'\[.*?\]', text)
             if match:
                 coords = json.loads(match.group(0))
                 if not coords: return f"Не можу знайти '{target}'."
                 
                 # Get real screen resolution
                 W, H = self.navigator.get_screen_size()
                 
                 ymin, xmin, ymax, xmax = coords
                 cx = int((xmin + xmax) / 2 / 1000 * W)
                 cy = int((ymin + ymax) / 2 / 1000 * H)
                 
                 return self.navigator.click_at(cx, cy)
             return "Не вдалося розпізнати координати."
        except Exception as e:
             return f"Помилка Vision: {e}"

    def handle_type_text(self, query: str, context, text: str = None) -> str:
        """Handler for type text"""
        if not text:
            text = query.replace("напиши", "").replace("введи", "").strip()

        if context:
            context.log_action(f"Operations: Typing '{text}'")
        return self.navigator.type_text(text)
    
    def handle_press_key(self, query: str, context, key: str = None) -> str:
        """Handler for press key command"""
        if not key:
             # Try to extract key from query if not provided
             # But usually CommandRegistry provides it via args_extractor
             return "Не вказано клавішу для натискання."
        
        if context: context.log_action(f"Operations: Pressing key '{key}'")
        return self.navigator.press_key(key)
    
    def web_search(self, query: str):
        import os
        url = f'https://www.perplexity.ai/search?q={query}'
        os.startfile(url)
        return f'Search for {query} sent to Perplexity.'
    
    # Видалено: _confirm_transaction - використовується confirm_command замість нього
    
    def confirm_command(self, confirmation: str) -> str:
        """
        Підтверджує виконання команди (для Safety Layer).
        
        Args:
            confirmation: "так", "виконай", "ні", "скасуй"
            
        Returns:
            Результат виконання або повідомлення про скасування
        """
        if not self.pending_command:
            return "Немає команди для підтвердження"
        
        confirmation_lower = confirmation.lower()
        
        if confirmation_lower in ["так", "виконай", "yes", "execute", "ok"]:
            # Виконуємо команду
            command = self.pending_command
            context = self.pending_context
            
            # Очищаємо pending
            self.pending_command = None
            self.pending_context = None
            
            success, output = self.shell_executor.execute(command)
            
            if success:
                if context:
                    context.log_action(f"Operations: Підтверджено та виконано: {command[:50]}...")
                # 🔇 Жорсткий фільтр виводу (The Silencer)
                # Повертаємо ТІЛЬКИ результат, без зайвих слів
                return output.strip() if output else ""
            else:
                return f"Помилка виконання: {output}"
        
        elif confirmation_lower in ["ні", "скасуй", "no", "cancel"]:
            # Скасовуємо
            command = self.pending_command
            self.pending_command = None
            self.pending_context = None
            return f"Команда скасована: {command[:50]}..."
        
        else:
            return "Не розумію. Скажіть 'так' для виконання або 'ні' для скасування."

    def _handle_code_analysis(self, query: str, context=None) -> str:
        """
        Виконує аналіз коду проекту (Self-Awareness).
        """
        if not self.model:
            return "Модель Brain не підключена. Не можу проаналізувати архітектуру."
            
        import os
        import threading
        current_dir = os.getcwd()

        # Check for specific file analysis
        if "file" in query.lower() or "файл" in query.lower():
            # Try to extract filename
            parts = query.split()
            target_file = None
            for p in parts:
                if p.endswith(".py") or p.endswith(".json") or p.endswith(".md"):
                    target_file = p
                    break
            
            if target_file and os.path.exists(target_file):
                try:
                    # Quick file analysis
                    with open(target_file, "r", encoding="utf-8") as f:
                        content = f.read(5000) # First 5KB
                    
                    prompt = f"ACT AS: Senior Developer. ANALYZE this file ({target_file}):\n\n{content}\n\nPROVIDE: Summary, Issues, Fixes."
                    response = self.model.generate_content(prompt)
                    return f"📄 Аналіз файлу {target_file}:\n{response.text}"
                except Exception as e:
                    return f"Помилка читання файлу: {e}"

        # Full Project Analysis (Background)
        def _run_analysis_async():
            try:
                print(f"🕵️ [OPERATIONS] Starting background code analysis of {current_dir}...")
                project_data = self.code_analyzer.scan_project(current_dir)
                prompt = self.code_analyzer.generate_roadmap_prompt(project_data)
                
                print("🧠 [OPERATIONS] Generating Architecture Report...")
                response = self.model.generate_content(prompt)
                
                result = response.text if response.text else "No report generated."
                
                print("\n" + "="*40)
                print("📊 PROJECT ARCHITECTURE REPORT")
                print("="*40)
                print(result)
                print("="*40 + "\n")
                
                # Save to file
                with open("PROJECT_ANALYSIS.md", "w", encoding="utf-8") as f:
                    f.write(result)
                print("✅ [OPERATIONS] Report saved to PROJECT_ANALYSIS.md")
                
            except Exception as e:
                print(f"❌ [OPERATIONS] Analysis failed: {e}")

        threading.Thread(target=_run_analysis_async, daemon=True).start()
        return "🔍 Розпочато повний аналіз проекту у фоні. Це займе хвилину. Звіт буде збережено у 'PROJECT_ANALYSIS.md'."

    def handle_workspace(self, query: str, context, project_name: str, action: str = "open_workspace") -> str:
        """
        Метод для керування робочим простором.
        Викликається через Brain -> Tools.
        """
        if not project_name:
            return "❌ Не вказано назву проекту."
            
        if action == "open_workspace":
            if context: context.log_action(f"Operations: Розгортання воркспейсу '{project_name}'")
            return self.scenario_manager.open_workspace(project_name)
        elif action == "find_project":
            path = self.launcher.find_project_globally(project_name)
            if path:
                return f"✅ Проект '{project_name}' знайдено за шляхом: {path}"
            return f"❌ Проект '{project_name}' не знайдено."
        
        return f"❌ Невідома дія воркспейсу: {action}"

    def screen_audit(self) -> str:
        """
        Робить скріншот екрана для подальшого аудиту.
        Зберігає у temp_audit.png.
        """
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            screenshot.save("temp_audit.png")
            return "temp_audit.png"
        except Exception as e:
            print(f"❌ [OPERATIONS] Помилка скріншоту для аудиту: {e}")
            return f"Error: {e}"



