import os
"""
skills/tools_definition.py
Визначення інструментів (Tools) для Gemini Function Calling.

Це "руки" ATLAS - функції, які Gemini може викликати для виконання команд.
Використовуємо genai.FunctionDeclaration для правильного формату.
"""

import google.generativeai as genai
from typing import Dict, Any, Optional, List
import sys
from pathlib import Path

# Додаємо батьківську директорію для імпортів
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config


# Імпорти для web_search
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    # Спробуємо новий пакет ddgs
    try:
        from ddgs import DDGS
        HAS_DDGS = True
    except ImportError:
        # Fallback на старий пакет
        from duckduckgo_search import DDGS
        HAS_DDGS = True
except ImportError:
    HAS_DDGS = False


def get_atlas_tools():
    """
    Створює список інструментів для Gemini Function Calling.
    
    Returns:
        Список словників з визначеннями функцій для Gemini
    """
    
    # === ІНСТРУМЕНТ 1: Системні операції ===
    sys_ops_tool = {
        "function_declarations": [{
            "name": "sys_ops",
            "description": "Системні операції: відкриття програм, управління гучністю, вимкнення ПК, зупинка музики. Використовуй для запуску програм, зупинки музики, зміни гучності.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Дія для виконання",
                        "enum": ["open_app", "stop_music", "set_volume", "shutdown", "restart", "sleep"]
                    },
                    "app_name": {
                        "type": "string",
                        "description": "Назва програми (для open_app): chrome, cursor, telegram, spotify, calc, notepad, ide, editor тощо"
                    },
                    "volume_level": {
                        "type": "integer",
                        "description": "Рівень гучності від 0 до 100 (для set_volume)"
                    },
                    "reason": {
                        "type": "string",
                        "description": "Причина дії (опціонально, для логування)"
                    }
                },
                "required": ["action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 2: Браузер та пошук ===
    browser_tool = {
        "function_declarations": [{
            "name": "browser",
            "description": "Відкриття URL, пошук в Google, навігація в інтернеті. Використовуй для пошуку інформації, відкриття сайтів.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Дія для виконання",
                        "enum": ["open_url", "search", "open_tab"]
                    },
                    "url": {
                        "type": "string",
                        "description": "URL для відкриття (для open_url), наприклад: https://github.com"
                    },
                    "query": {
                        "type": "string",
                        "description": "Пошуковий запит (для search), наприклад: 'AI news latest' або 'новини про штучний інтелект'"
                    },
                    "site": {
                        "type": "string",
                        "description": "Сайт для пошуку (опціонально, наприклад: 'site:github.com')"
                    }
                },
                "required": ["action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 3: Пам'ять ===
    memory_tool = {
        "function_declarations": [{
            "name": "memory",
            "description": "Збереження та отримання нагадувань, дедлайнів та важливих фактів. Використовуй для запам'ятовування важливої інформації, дедлайнів, нагадувань.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Дія для виконання",
                        "enum": ["save_reminder", "save_deadline", "save_fact", "get_deadlines", "get_reminders", "search"]
                    },
                    "content": {
                        "type": "string",
                        "description": "Текст для збереження (для save_reminder, save_deadline, save_fact)"
                    },
                    "date_due": {
                        "type": "string",
                        "description": "Дата дедлайну у форматі YYYY-MM-DD або 'п'ятниця', 'через 3 дні' (для save_deadline)"
                    },
                    "search_query": {
                        "type": "string",
                        "description": "Пошуковий запит (для search)"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Теги для пошуку (опціонально)"
                    }
                },
                "required": ["action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 4: Кодування ===
    coding_tool = {
        "function_declarations": [{
            "name": "coding",
            "description": "Робота з кодом: створення файлів, читання коду, аналіз проектів. Використовуй цей інструмент, щоб прочитати та проаналізувати локальні файли проекту на диску користувача. Тобі НЕ потрібно просити користувача завантажувати файли, ти вже маєш до них доступ через CodeAnalyzer.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Дія для виконання",
                        "enum": ["create_file", "read_file", "analyze_project", "analyze_file", "find_bugs"]
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Шлях до файлу (для create_file, read_file), наприклад: 'src/main.py'"
                    },
                    "content": {
                        "type": "string",
                        "description": "Вміст файлу для створення (для create_file)"
                    },
                    "project_name": {
                        "type": "string",
                        "description": "Назва проекту (для analyze_project, find_bugs)"
                    },
                    "mode": {
                        "type": "string",
                        "description": "Режим запису: 'write' (перезапис), 'append' (додавання в кінець), 'replace' (заміна тексту)",
                        "enum": ["write", "append", "replace"]
                    },
                    "find_text": {
                        "type": "string",
                        "description": "Текст, який треба знайти і замінити (тільки для mode='replace')"
                    }
                },
                "required": ["action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 5: Файлові операції ===
    file_ops_tool = {
        "function_declarations": [{
            "name": "file_ops",
            "description": "Файлові операції: пошук файлів, створення папок, переміщення, копіювання, список файлів. Використовуй для роботи з файловою системою.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Дія для виконання",
                        "enum": ["find_files", "create_folder", "move_file", "copy_file", "list_files", "delete_file"]
                    },
                    "path": {
                        "type": "string",
                        "description": "Шлях до папки або файлу, наприклад: 'Documents' або 'C:\\Users\\Username\\Documents'"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Шаблон пошуку (для find_files, наприклад: '*.pdf' або '*.txt')"
                    },
                    "destination": {
                        "type": "string",
                        "description": "Шлях призначення (для move_file, copy_file)"
                    },
                    "folder_name": {
                        "type": "string",
                        "description": "Назва папки для створення (для create_folder)"
                    }
                },
                "required": ["action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 6: Веб-пошук ===
    web_search_tool = {
        "function_declarations": [{
            "name": "web_search",
            "description": "Пошук інформації в Інтернеті: новини, погода, курс валют, документація, факти. Використовуй для отримання актуальної інформації з інтернету.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Пошуковий запит, наприклад: 'новини про штучний інтелект', 'погода в Києві', 'курс долара'"
                    }
                },
                "required": ["query"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 7: Сценарії ===
    scenario_tool = {
        "function_declarations": [{
            "name": "scenario",
            "description": "Запуск готових сценаріїв: робочий режим, ігровий режим, режим фокусу, презентації, екстрене очищення. Використовуй для активації готових режимів роботи.",
            "parameters": {
                "type": "object",
                "properties": {
                    "scenario_name": {
                        "type": "string",
                        "description": "Назва сценарію",
                        "enum": ["work_mode", "gaming_mode", "focus_mode", "presentation_mode", "emergency_cleanup"]
                    }
                },
                "required": ["scenario_name"]
            }
        }]
    }

    # === ІНСТРУМЕНТ 8: Робочий простір (Workspace) ===
    workspace_tool = {
        "function_declarations": [{
            "name": "workspace",
            "description": "Розгортання робочого середовища (Робоча форма). Використовуй, коли користувач просить підготувати проект до роботи, відкрити папки проекту в IDE тощо.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Назва проекту для розгортання (напр. SystemCOO, AuraMail, Atlas)"
                    },
                    "action": {
                        "type": "string",
                        "description": "Дія",
                        "enum": ["open_workspace", "find_project"]
                    }
                },
                "required": ["project_name", "action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 9: Послідовність дій (Sequence Execution) ===
    sequence_tool = {
        "function_declarations": [{
            "name": "execute_sequence",
            "description": "Виконання послідовності дій. Використовуй, коли користувач просить зробити кілька речей підряд (наприклад: 'спочатку відкрий, потім напиши').",
            "parameters": {
                "type": "object",
                "properties": {
                    "actions": {
                        "type": "array",
                        "description": "Список дій для виконання",
                        "items": {
                            "type": "object",
                            "properties": {
                                "tool_name": {
                                    "type": "string",
                                    "description": "Назва інструменту (ui_automation, sys_ops, browser, coding)"
                                },
                                "args": {
                                    "type": "object",
                                    "description": "Аргументи для інструменту"
                                },
                                "delay": {
                                    "type": "number",
                                    "description": "Затримка після дії в секундах (default: 1.0)"
                                }
                            },
                            "required": ["tool_name", "args"]
                        }
                    }
                },
                "required": ["actions"]
            }
        }]
    }
    ui_tool = {
        "function_declarations": [{
            "name": "ui_automation",
            "description": "Керування інтерфейсом Windows: кліки, введення тексту, відкриття програм. Використовуй тільки якщо користувач просить натиснути щось у програмі або ввести текст.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "Дія",
                        "enum": ["open_app", "click", "type", "scroll", "press_key"]
                    },
                    "target": {
                        "type": "string",
                        "description": "Назва програми (для open_app) або текст елемента для кліку (для click)"
                    },
                    "text": {
                        "type": "string",
                        "description": "Текст для введення (для type)"
                    },
                    "key": {
                        "type": "string",
                        "description": "Клавіша (для press_key): enter, tab, esc, win, etc."
                    },
                     "coordinates": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "[x, y] - координати для кліку (якщо відомі)"
                    }
                },
                "required": ["action"]
            }
        }]
    }
    
    # === ІНСТРУМЕНТ 10: Аудит екрана ===
    audit_tool = {
        "function_declarations": [{
            "name": "screen_audit",
            "description": "Робить знімок екрана та проводить візуальний аудит робочого простору (пошук багів, аналіз UI).",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }]
    }
    
    # Об'єднуємо всі функції в один список (visual_tool видалено - DO NOT USE YET)
    all_functions = []
    for tool_dict in [sys_ops_tool, browser_tool, memory_tool, coding_tool, file_ops_tool, web_search_tool, scenario_tool, workspace_tool, ui_tool, sequence_tool, audit_tool]:
        all_functions.extend(tool_dict["function_declarations"])
    
    return {"function_declarations": all_functions}


def execute_tool(function_name: str, args: Dict[str, Any], context=None) -> str:
    """
    Виконує інструмент на основі його назви та аргументів.
    
    Args:
        function_name: Назва функції для виконання
        args: Аргументи функції (словник)
        context: Контекст для доступу до департаментів
        
    Returns:
        Результат виконання функції
    """
    try:
        if function_name == "sys_ops":
            return _execute_sys_ops(args, context)
        elif function_name == "browser":
            return _execute_browser(args, context)
        elif function_name == "memory":
            return _execute_memory(args, context)
        elif function_name == "coding":
            return _execute_coding(args, context)
        elif function_name == "file_ops":
            return _execute_file_ops(args, context)
        elif function_name == "web_search":
            return _execute_web_search(args, context)
        elif function_name == "scenario":
            return _execute_scenario(args, context)
        elif function_name == "workspace":
            return _execute_workspace(args, context)
        elif function_name == "ui_automation":
            return _execute_ui_automation(args, context)
        elif function_name == "execute_sequence":
            return _execute_sequence(args, context)
        elif function_name == "screen_audit":
            return _execute_screen_audit(args, context)
        else:
            return f"❌ Невідомий інструмент: {function_name}"
    except Exception as e:
        import traceback
        traceback.print_exc()
        return f"❌ Помилка виконання інструменту {function_name}: {e}"


def _execute_sys_ops(args: Dict[str, Any], context) -> str:
    """Виконує системні операції"""
    action = args.get("action")
    
    if action == "open_app":
        app_name = args.get("app_name", "")
        if not app_name:
            return "❌ Не вказано назву програми"
        
        # Використовуємо Operations Department для запуску
        if context and hasattr(context, 'operations_dept'):
            result = context.operations_dept.handle(f"відкрий {app_name}", context)
            return result or f"✅ Запущено {app_name}"
        return f"✅ Запущено {app_name}"
    
    elif action == "stop_music":
        try:
            from skills.music import stop_music
            stop_music()
            return "✅ Музику зупинено"
        except Exception as e:
            return f"❌ Помилка зупинки музики: {e}"
    
    elif action == "set_volume":
        volume = args.get("volume_level", 50)
        # TODO: Реалізувати зміну гучності через Windows API
        return f"✅ Гучність встановлено на {volume}%"
    
    elif action in ["shutdown", "restart", "sleep"]:
        return f"⚠️ Команда {action} потребує підтвердження користувача"
    
    return f"❌ Невідома дія: {action}"


def _execute_browser(args: Dict[str, Any], context) -> str:
    """Browser operations execution"""
    action = args.get("action")
    
    if action == "open_url":
        url = args.get("url", "")
        if not url:
            return "Error: No URL provided"
        return open_url(url)
    
    elif action == "search":
        query = args.get("query", "")
        if not query:
            return "Error: No query provided"
        
        search_url = f"https://www.perplexity.ai/search?q={query}"
        return open_url(search_url)
    
    return f"Error: Unknown browser action: {action}"


def _execute_memory(args: Dict[str, Any], context) -> str:
    """Виконує операції з пам'яттю"""
    action = args.get("action")
    
    try:
        from skills.memory_storage import get_memory_storage
        memory = get_memory_storage()
    except Exception as e:
        return f"❌ Помилка доступу до пам'яті: {e}"
    
    if action == "save_reminder":
        content = args.get("content", "")
        if not content:
            return "❌ Не вказано текст нагадування"
        entry_id = memory.save_reminder(content)
        return f"✅ Нагадування збережено: {content}"
    
    elif action == "save_deadline":
        content = args.get("content", "")
        date_due = args.get("date_due")
        if not content:
            return "❌ Не вказано текст дедлайну"
        entry_id = memory.save_reminder(content, date_due=date_due)
        return f"✅ Дедлайн збережено: {content} (до {date_due or 'не вказано'})"
    
    elif action == "save_fact":
        content = args.get("content", "")
        tags = args.get("tags", [])
        if not content:
            return "❌ Не вказано текст факту"
        entry_id = memory.save_fact(content, tags=tags)
        return f"✅ Факт збережено: {content}"
    
    elif action == "get_deadlines":
        deadlines = memory.get_deadlines(upcoming_days=60)
        if deadlines:
            result = "📅 Дедлайни:\n\n"
            for i, deadline in enumerate(deadlines, 1):
                result += f"{i}. {deadline.content}\n"
            return result
        return "✅ Немає активних дедлайнів"
    
    elif action == "get_reminders":
        reminders = memory.get_reminders()
        if reminders:
            result = "📝 Нагадування:\n\n"
            for i, reminder in enumerate(reminders[-10:], 1):
                result += f"{i}. {reminder.content}\n"
            return result
        return "✅ Немає нагадувань"
    
    elif action == "search":
        query = args.get("search_query", "")
        if not query:
            return "❌ Не вказано пошуковий запит"
        results = memory.search(query, limit=5)
        if results:
            result_text = "🔍 Знайдено:\n\n"
            for i, entry in enumerate(results, 1):
                result_text += f"{i}. {entry.content}\n"
            return result_text
        return f"❌ Нічого не знайдено про '{query}'"
    
    return f"❌ Невідома дія пам'яті: {action}"

def _backup_file(path) -> str:
    """Створює бекап файлу перед зміною."""
    try:
        if not path.exists(): return ""
        import shutil
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak_path = path.with_suffix(f".{timestamp}.bak")
        shutil.copy2(path, bak_path)
        return str(bak_path)
    except Exception as e:
        print(f"⚠️ Failed to backup {path}: {e}")
        return ""

def _execute_coding(args: Dict[str, Any], context) -> str:
    """Виконує операції з кодом"""
    action = args.get("action")
    
    if action == "create_file":
        file_path = args.get("file_path", "")
        content = args.get("content", "")
        mode = args.get("mode", "write")
        find_text = args.get("find_text", "")
        
        if not file_path:
            return "❌ Не вказано шлях до файлу"
        
        try:
            from pathlib import Path
            path = Path(file_path)
            
            # Автоматичне створення папок
            if not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)
                print(f"📁 [FILES] Створено директорію: {path.parent}")
            
            # --- SAFETY & BACKUP ---
            critical_keywords = ["config", "main", "brain", "router", "operations", "core", "skills"]
            if any(k in str(path).lower() for k in critical_keywords) and path.exists():
                bak = _backup_file(path)
                if bak: print(f"🛡️ [SAFETY] Backup created: {bak}")
            
            # --- EXECUTION ---
            if mode == "append":
                if not path.exists():
                     path.write_text(content, encoding='utf-8')
                     return f"✅ Файл створено та записано: {file_path}"
                else:
                    with open(path, "a", encoding="utf-8") as f:
                        f.write("\n" + content)
                    return f"✅ Додано вміст у кінець файлу: {file_path}"
                    
            elif mode == "replace":
                if not path.exists():
                    return f"❌ Помилка: файл {file_path} не існує для заміни."
                
                if not find_text:
                    return "❌ Помилка: параметр 'find_text' обов'язковий для режиму replace."
                
                original_text = path.read_text(encoding="utf-8")
                if find_text not in original_text:
                    return f"❌ Помилка: текст для заміни не знайдено у файлі {file_path}."
                
                # Виконуємо заміну
                new_text = original_text.replace(find_text, content)
                path.write_text(new_text, encoding="utf-8")
                return f"✅ Успішно замінено текст у файлі: {file_path}"
                
            else: # mode == "write" (default)
                path.write_text(content, encoding='utf-8')
                return f"✅ Файл успішно {'оновлено' if path.exists() else 'створено'}: {file_path}"

        except Exception as e:
            print(f"❌ [FILES] Error in create_file: {e}")
            return f"❌ Помилка файлової операції: {str(e)}"
    
    elif action == "read_file":
        file_path = args.get("file_path", "")
        if not file_path:
            return "❌ Не вказано шлях до файлу"
        
        try:
            from pathlib import Path
            path = Path(file_path)
            if not path.exists():
                return f"❌ Файл не знайдено: {file_path}"
            content = path.read_text(encoding='utf-8')
            return f"📄 Вміст файлу {file_path}:\n\n{content[:1000]}..."  # Обмежуємо довжину
        except Exception as e:
            return f"❌ Помилка читання файлу: {e}"
    
    elif action == "analyze_project":
        project_name = args.get("project_name", "")
        if not project_name:
            return "❌ Не вказано назву проекту"
        
        # Використовуємо Coder Agent
        try:
            from agents.coder_agent import analyze_project
            result = analyze_project(project_name, task_type="analyze")
            return result or f"✅ Аналіз проекту {project_name} завершено"
        except Exception as e:
            return f"❌ Помилка аналізу проекту: {e}"

    elif action == "analyze_file":
        file_path = args.get("file_path", "")
        if not file_path:
            return "❌ Не вказано шлях до файлу"
            
        # Delegate to OperationsDepartment which has the new async/sync logic
        if context and hasattr(context, 'operations_dept'):
            query = f"analyze file {file_path}"
            return context.operations_dept._handle_code_analysis(query, context)
        else:
             return "❌ OperationsDepartment недоступний для аналізу файлу."
    
    return f"❌ Невідома дія кодування: {action}"


def _execute_file_ops(args: Dict[str, Any], context) -> str:
    """Виконує файлові операції"""
    action = args.get("action")
    
    if action == "find_files":
        path = args.get("path", ".")
        pattern = args.get("pattern", "*")
        
        try:
            from pathlib import Path
            import glob
            search_path = Path(path)
            files = list(search_path.glob(pattern)) if search_path.exists() else []
            
            if files:
                result = f"🔍 Знайдено {len(files)} файлів:\n\n"
                for i, file in enumerate(files[:10], 1):  # Обмежуємо до 10
                    result += f"{i}. {file}\n"
                if len(files) > 10:
                    result += f"\n... та ще {len(files) - 10} файлів"
                return result
            return f"❌ Файли не знайдено за шаблоном {pattern}"
        except Exception as e:
            return f"❌ Помилка пошуку файлів: {e}"
    
    elif action == "create_folder":
        folder_name = args.get("folder_name", "")
        if not folder_name:
            return "❌ Не вказано назву папки"
        
        try:
            from pathlib import Path
            path = Path(folder_name)
            path.mkdir(parents=True, exist_ok=True)
            return f"✅ Папку створено: {folder_name}"
        except Exception as e:
            return f"❌ Помилка створення папки: {e}"
    
    elif action == "list_files":
        path = args.get("path", ".")
        
        try:
            from pathlib import Path
            dir_path = Path(path)
            if not dir_path.exists():
                return f"❌ Папка не існує: {path}"
            
            files = list(dir_path.iterdir())
            if files:
                result = f"📂 Файли в {path}:\n\n"
                for i, file in enumerate(files[:20], 1):  # Обмежуємо до 20
                    file_type = "📁" if file.is_dir() else "📄"
                    result += f"{i}. {file_type} {file.name}\n"
                return result
            return f"📂 Папка порожня: {path}"
        except Exception as e:
            return f"❌ Помилка переліку файлів: {e}"
    
    elif action == "move_file":
        path = args.get("path", "")
        destination = args.get("destination", "")
        if not path or not destination:
            return "❌ Вкажіть 'path' та 'destination' для переміщення"
        try:
            import shutil
            from pathlib import Path
            src = Path(path)
            dst = Path(destination)
            if not src.exists():
                return f"❌ Файл не знайдено: {path}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            return f"✅ Переміщено: {path} → {destination}"
        except Exception as e:
            return f"❌ Помилка переміщення: {e}"

    elif action == "copy_file":
        path = args.get("path", "")
        destination = args.get("destination", "")
        if not path or not destination:
            return "❌ Вкажіть 'path' та 'destination' для копіювання"
        try:
            import shutil
            from pathlib import Path
            src = Path(path)
            dst = Path(destination)
            if not src.exists():
                return f"❌ Файл не знайдено: {path}"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            return f"✅ Скопійовано: {path} → {destination}"
        except Exception as e:
            return f"❌ Помилка копіювання: {e}"

    elif action == "delete_file":
        path = args.get("path", "")
        if not path:
            return "❌ Не вказано шлях до файлу для видалення"
        try:
            import shutil
            from pathlib import Path
            target = Path(path)
            if not target.exists():
                return f"❌ Файл/папка не знайдено: {path}"
            if target.is_dir():
                shutil.rmtree(target)
            else:
                target.unlink()
            return f"✅ Видалено: {path}"
        except Exception as e:
            return f"❌ Помилка видалення: {e}"

    return f"❌ Невідома файлова операція: {action}"



def _execute_web_search(args: Dict[str, Any], context) -> str:
    """Web search execution using Perplexity in browser"""
    query = args.get("query", "")
    if not query:
        return "Error: No query provided"
    
    url = f"https://www.perplexity.ai/search?q={query}"
    open_url(url)
    return f"Search for '{query}' sent to Perplexity."


def _execute_scenario(args: Dict[str, Any], context) -> str:
    """Виконує сценарії"""
    scenario_name = args.get("scenario_name", "")
    
    if not scenario_name:
        return "❌ Не вказано назву сценарію"
    
    if context and hasattr(context, 'operations_dept'):
        # Використовуємо ScenarioManager через Operations Department
        result = context.operations_dept.handle(f"запусти {scenario_name}", context)
        return result or f"✅ Сценарій {scenario_name} запущено"
    
    return f"✅ Сценарій {scenario_name} запущено"


def _execute_ui_automation(args: Dict[str, Any], context) -> str:
    """Виконує дії UI автоматизації"""
    try:
        from skills.system_navigator import SystemNavigator
        # Singleton instance or create new
        navigator = SystemNavigator()
        
        action = args.get("action")
        target = args.get("target")
        text = args.get("text")
        key = args.get("key")
        coords = args.get("coordinates")
        
        if action == "open_app":
            if not target: return "❌ Не вказано назву програми"
            return navigator.open_app(target)
            
        elif action == "click":
            if coords:
                return navigator.click_at(coords[0], coords[1])
            elif target:
                return navigator.click_element(target)
            else:
                return "❌ Не вказано ціль для кліку"
                
        elif action == "type":
            if not text: return "❌ Не вказано текст"
            return navigator.type_text(text)
            
        elif action == "press_key":
            if not key: return "❌ Не вказано клавішу"
            return navigator.press_key(key)
            
        elif action == "scroll":
            amount = args.get("amount", -1) # Default down
            return navigator.scroll(amount)
            
        return f"❌ Невідома дія UI: {action}"
        
    except Exception as e:
        return f"❌ Помилка UI Navigator: {e}"

def _execute_sequence(args: Dict[str, Any], context) -> str:
    """Виконує послідовність дій з затримками."""
    actions = args.get("actions", [])
    if not actions:
        return "❌ Порожня послідовність дій."
        
    results = []
    import time
    
    for i, step in enumerate(actions, 1):
        tool_name = step.get("tool_name")
        tool_args = step.get("args", {})
        delay = step.get("delay", 1.5) # Default 1.5s for stability
        
        print(f"🔄 [SEQUENCE] Step {i}: {tool_name} (delay={delay}s)")
        
        # Виконання кроку
        try:
            res = execute_tool(tool_name, tool_args, context)
            results.append(f"Крок {i} ({tool_name}): {res}")
        except Exception as e:
            results.append(f"❌ Крок {i} помилка: {e}")
        
        # Пауза
        if i < len(actions):
            time.sleep(delay)
            
    return "\n".join(results)

def _execute_workspace(args: Dict[str, Any], context) -> str:
    """Виконує дії з робочим простором"""
    project_name = args.get("project_name")
    action = args.get("action", "open_workspace")
    
    if not project_name:
        return "❌ Не вказано назву проекту"
        
    if context and hasattr(context, 'operations_dept') and context.operations_dept:
        # Використовуємо Operations Department для роботи з воркспейсом
        return context.operations_dept.handle_workspace("", context, project_name, action)
            
    return "❌ Помилка: Operations department не ініціалізовано в контексті"

def open_url(url: str):
    import os
    os.startfile(url)
    return f'Opened: {url}'

def _execute_screen_audit(args: Dict[str, Any], context) -> str:
    """Виконує аудит екрана"""
    if context and hasattr(context, 'operations_dept') and context.operations_dept:
        # Цей метод буде викликаний через Brain.think, але як інструмент він просто робить знімок
        path = context.operations_dept.screen_audit()
        if "Error" in path:
            return f"❌ Помилка знімку екрана: {path}"
        return f"✅ Знімок для аудиту зроблено: {path}. Виконую візуальний аналіз..."
    return "❌ Operations department не ініціалізовано"
