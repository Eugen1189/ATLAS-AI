"""
Router для маршрутизації команд між департаментами.

Router отримує запит, перевіряє департаменти за пріоритетом,
і передає запит першому департаменту, який може його обробити.
"""

import subprocess
import threading
import time
import sys
import re
from pathlib import Path
from .context import Context

# Імпорт Queue Manager
try:
    root_dir = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root_dir))
    from agents.queue_manager import get_queue_manager, TaskStatus
    HAS_QUEUE_MANAGER = True
except ImportError as e:
    HAS_QUEUE_MANAGER = False
    get_queue_manager = None
    TaskStatus = None
    print(f"⚠️ [ROUTER] Queue Manager не знайдено, використовується прямий запуск: {e}")


class AgentLauncher:
    """Запускає агенти як окремі процеси"""
    
    def __init__(self):
        self.root_dir = Path(__file__).resolve().parent.parent
        import config
        self.inbox_dir = config.INBOX_DIR
        self.inbox_dir.mkdir(parents=True, exist_ok=True)
        print("✅ [AGENT LAUNCHER] Ініціалізовано")
    
    def launch_coder(self, project_name: str, task_type: str = "analyze", query: str = "") -> str:
        """
        Запускає coder_agent.py через Queue Manager або напряму.
        
        Args:
            project_name: Назва проекту
            task_type: Тип задачі (analyze, find_bugs, generate_module, refactor)
            query: Оригінальний запит користувача
            
        Returns:
            Повідомлення користувачу (не чекає результату)
        """
        # Перевіряємо, чи є Queue Manager
        if hasattr(self, 'queue_manager') and self.queue_manager:
            # Використовуємо Queue Manager
            task_id = self.queue_manager.add_task(
                agent_type="coder",
                task_type=task_type,
                project_name=project_name,
                context=query,
                priority=7  # Високий пріоритет для Coder Agent
            )
            
            task_names = {
                "analyze": "аналіз проекту",
                "find_bugs": "пошук багів",
                "generate_module": "генерацію модуля",
                "refactor": "рефакторинг коду"
            }
            task_name = task_names.get(task_type, "задачу")
            
            return f"💻 Додано {task_name} для проекту '{project_name}' до черги (ID: {task_id[:8]}...). Результат буде в папці CodeAnalysis."
        
        # Fallback: прямий запуск (якщо Queue Manager недоступний)
        agent_path = self.root_dir / "agents" / "coder_agent.py"
        
        if not agent_path.exists():
            return f"❌ Помилка: Агент coder_agent.py не знайдено в {agent_path}"
        
        task_names = {
            "analyze": "аналіз проекту",
            "find_bugs": "пошук багів",
            "generate_module": "генерацію модуля",
            "refactor": "рефакторинг коду"
        }
        task_name = task_names.get(task_type, "задачу")
        
        try:
            subprocess.Popen([
                "python", 
                str(agent_path),
                project_name,
                "--task", task_type,
                "--context", query
            ], cwd=str(self.root_dir))
            
            print(f"🚀 [AGENT LAUNCHER] Запущено Coder Agent ({task_type}): {project_name}")
            return f"💻 Виконую {task_name} для проекту '{project_name}'. Результат буде в папці CodeAnalysis."
        except Exception as e:
            print(f"❌ [AGENT LAUNCHER] Помилка запуску агента: {e}")
            return f"❌ Помилка запуску агента: {e}"
    
    def check_inbox(self) -> list:
        """
        Перевіряє папку Inbox на нові файли _DONE
        
        Returns:
            Список нових файлів
        """
        done_files = []
        if not self.inbox_dir.exists():
            return done_files
            
        for file in self.inbox_dir.glob("*_DONE.txt"):
            # Перевіряємо час модифікації (щоб не показувати старі)
            if time.time() - file.stat().st_mtime < 60:  # Останні 60 секунд
                done_files.append(file)
        return done_files


class Router:
    """
    Маршрутизатор команд до департаментів.
    
    Працює за принципом пріоритетів:
    1. Перевіряє Operations Department
    2. Якщо Operations не підходить - повертаємо повідомлення про помилку
    """
    
    def __init__(self, model=None):
        """
        Ініціалізація Router.
        
        Args:
            model: Gemini модель (для департаментів, які її потребують)
        """
        self.model = model
        self.context = Context()
        self.departments = []
        
        # Ініціалізація Queue Manager
        if HAS_QUEUE_MANAGER:
            try:
                self.queue_manager = get_queue_manager()
                # Реєструємо callback для сповіщень про статус
                self.queue_manager.register_status_callback(self._on_task_status_change)
                print("✅ [ROUTER] Queue Manager підключено")
            except Exception as e:
                print(f"⚠️ [ROUTER] Помилка ініціалізації Queue Manager: {e}")
                self.queue_manager = None
        else:
            self.queue_manager = None
        
        # Ініціалізуємо AgentLauncher з посиланням на queue_manager
        self.agent_launcher = AgentLauncher()
        self.agent_launcher.queue_manager = self.queue_manager
        
        from .memory_storage import get_memory_storage
        self.memory = get_memory_storage()
        
        print("🔄 [ROUTER] Ініціалізація маршрутизатора...")
        self.load_departments()
        print(f"✅ [ROUTER] Завантажено {len(self.departments)} департаментів")
        print("✅ [ROUTER] Ініціалізовано")
    
    def load_departments(self):
        """Завантажує всі департаменти та сортує за пріоритетом"""
        try:
            # Імпортуємо департаменти
            from .departments.operations import OperationsDepartment
            from .departments.vision import VisionDepartment
            
            # Створюємо департаменти
            operations_dept = OperationsDepartment()
            operations_dept.set_model(self.model)  # Встановлюємо модель для генерації команд
            
            vision_dept = VisionDepartment()
            
            self.departments = [
                vision_dept,      # Пріоритет: 3 (вищий за Operations)
                operations_dept,   # Пріоритет: 4
            ]
            
            # Встановлюємо посилання в контексті
            self.context.vision_dept = vision_dept
            self.context.operations_dept = operations_dept
            
            # Сортуємо за пріоритетом (1 = найвищий)
            self.departments.sort(key=lambda d: d.priority)
            
            print(f"✅ [ROUTER] Завантажено {len(self.departments)} департаментів: Vision, Operations")
            
        except Exception as e:
            print(f"⚠️ [ROUTER] Помилка завантаження департаментів: {e}")
            import traceback
            traceback.print_exc()
            self.departments = []
    
    def route(self, query: str) -> str:
        """
        Маршрутизує запит до відповідного департаменту або агента.
        Uses fallback logic since primary command matching happens in Brain.
        """
        if not query: return ""
        
        # 0. Intent Cache removed (it prevents repeated actions like 'open browser' from executing)
        
        print(f"🎯 [ROUTER] Маршрутизація запиту: {query[:50]}...")
        query_lower = query.lower().strip()
        result = None
        
        # 3. Heavy Operations removed - handled by Orchestrator/Brain
        pass
             
        # 4. Confirmation Check
        operations_dept = next((d for d in self.departments if d.name == "Operations"), None)
        if operations_dept and hasattr(operations_dept, 'pending_command') and operations_dept.pending_command:
            confirmation_keywords = ["так", "виконай", "ні", "скасуй", "yes", "no", "execute", "cancel"]
            if any(kw in query_lower for kw in confirmation_keywords):
                result = operations_dept.confirm_command(query)
                if result: 
                    self.memory.save_intent_cache(query, result)
                    return result


        
        # Save to cache if found a result
        if result:
            self.memory.save_intent_cache(query, result)
            
        return result
    




    def get_status(self) -> dict:
        return {
            "departments_count": len(self.departments),
            "active_project": self.context.get_active_project(),
            "recent_actions": self.context.get_recent_actions(),
        }

    async def _async_dispatch(self, query: str, intent: str):
        """Асинхронна обгортка для маршрутизації"""
        try:
            # Виконуємо синхронний route у пулі потоків, щоб не блокувати event loop
            import asyncio
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(None, self.route, query)
            if result:
                print(f"🎯 [ROUTER] Zone intent '{intent}' -> {result[:60]}...")
        except Exception as e:
            print(f"⚠️ [ROUTER] _async_dispatch error ({intent}): {e}")

    def dispatch_vision_intent(self, intent: str) -> None:
        """
        Викликається з VisionManager при спрацюванні віртуальних зон (dwell).
        Використовує asyncio.create_task для неблокуючого виконання.
        Інтенти: open_browser, toggle_media.
        """
        import asyncio
        import threading
        
        intent_queries = {
            "open_browser": "відкрий хром",
            "toggle_media": "пауза відтворення",
            "show_desktop": "покажи робочий стіл",
            "switch_window": "переключи вікно",
        }
        query = intent_queries.get(intent)
        if not query:
            return

        try:
            # Намагаємося отримати існуючий loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Якщо loop вже запущений (напр. у Flet або main), плануємо задачу
                loop.create_task(self._async_dispatch(query, intent))
            else:
                # Якщо loop є, але не запущений, запускаємо в окремому потоці через asyncio.run
                threading.Thread(target=lambda: asyncio.run(self._async_dispatch(query, intent)), daemon=True).start()
        except RuntimeError:
            # Якщо loop взагалі не створено для цього потоку
            threading.Thread(target=lambda: asyncio.run(self._async_dispatch(query, intent)), daemon=True).start()
