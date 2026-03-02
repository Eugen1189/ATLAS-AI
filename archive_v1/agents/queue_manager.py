"""
Queue Manager - Система черги та відстеження агентів.

Відповідає за:
1. Управління чергою агентів
2. Відстеження статусу виконання
3. Пріоритизацію задач
4. Паралельне виконання
"""
import os
import json
import threading
import subprocess
import time
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict

# Налаштування шляхів (використовуємо централізований config)
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


class TaskStatus(Enum):
    """Статуси виконання задачі"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentTask:
    """Задача для агента"""
    id: str
    agent_type: str  # "writer", "smm", "coder"
    task_type: str  # "analyze", "generate_module", etc.
    project_name: Optional[str] = None
    topic: Optional[str] = None
    context: str = ""
    priority: int = 5  # 1-10, де 10 - найвищий пріоритет
    status: TaskStatus = TaskStatus.PENDING
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result_path: Optional[str] = None
    error: Optional[str] = None
    progress: int = 0  # 0-100
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class AgentQueueManager:
    """
    Менеджер черги агентів.
    
    Відповідає за:
    - Додавання задач до черги
    - Відстеження статусу
    - Паралельне виконання
    - Пріоритизацію
    """
    
    def __init__(self, max_parallel: int = 3):
        """
        Ініціалізація менеджера черги.
        
        Args:
            max_parallel: Максимальна кількість агентів, що виконуються одночасно
        """
        self.max_parallel = max_parallel
        self.tasks: Dict[str, AgentTask] = {}
        self.running_tasks: Dict[str, subprocess.Popen] = {}
        self.lock = threading.Lock()
        self.status_callbacks: List[Callable] = []
        
        # Папка для збереження стану
        # Використовуємо централізований шлях з config
        self.state_dir = config.AGENT_QUEUE_STATE_DIR
        os.makedirs(self.state_dir, exist_ok=True)
        
        # Завантажуємо збережений стан
        self._load_state()
        
        # Запускаємо фонову обробку
        self.is_running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        print(f"✅ [QUEUE MANAGER] Ініціалізовано (max_parallel={max_parallel})")
    
    def add_task(self, agent_type: str, task_type: str, **kwargs) -> str:
        """
        Додає задачу до черги.
        
        Args:
            agent_type: Тип агента ("writer", "smm", "coder")
            task_type: Тип задачі
            **kwargs: Додаткові параметри (project_name, topic, context, priority)
            
        Returns:
            ID задачі
        """
        task_id = f"{agent_type}_{task_type}_{int(time.time() * 1000)}"
        
        task = AgentTask(
            id=task_id,
            agent_type=agent_type,
            task_type=task_type,
            project_name=kwargs.get("project_name"),
            topic=kwargs.get("topic"),
            context=kwargs.get("context", ""),
            priority=kwargs.get("priority", 5)
        )
        
        with self.lock:
            self.tasks[task_id] = task
            self._save_state()
        
        print(f"📥 [QUEUE MANAGER] Додано задачу: {task_id} ({agent_type}/{task_type})")
        self._notify_status_change(task_id)
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[AgentTask]:
        """
        Отримує статус задачі.
        
        Args:
            task_id: ID задачі
            
        Returns:
            AgentTask або None
        """
        with self.lock:
            return self.tasks.get(task_id)
    
    def get_all_tasks(self) -> List[AgentTask]:
        """
        Отримує всі задачі.
        
        Returns:
            Список задач
        """
        with self.lock:
            return list(self.tasks.values())
    
    def get_running_tasks(self) -> List[AgentTask]:
        """
        Отримує задачі, що виконуються зараз.
        
        Returns:
            Список виконуваних задач
        """
        with self.lock:
            return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]
    
    def get_pending_tasks(self) -> List[AgentTask]:
        """
        Отримує задачі в черзі.
        
        Returns:
            Список задач в черзі
        """
        with self.lock:
            return [task for task in self.tasks.values() if task.status == TaskStatus.PENDING]
    
    def register_status_callback(self, callback: Callable[[str, AgentTask], None]):
        """
        Реєструє callback для змін статусу.
        
        Args:
            callback: Функція, яка викликається при зміні статусу
                     Приймає (task_id, task)
        """
        self.status_callbacks.append(callback)
    
    def _worker_loop(self):
        """Фоновий потік для обробки черги"""
        while self.is_running:
            try:
                # Перевіряємо завершені процеси
                self._check_completed_processes()
                
                # Запускаємо нові задачі, якщо є місце
                self._start_pending_tasks()
                
                time.sleep(2)  # Перевірка кожні 2 секунди
            except Exception as e:
                print(f"❌ [QUEUE MANAGER] Помилка в worker_loop: {e}")
                time.sleep(5)
    
    def _check_completed_processes(self):
        """Перевіряє завершені процеси та оновлює статуси"""
        with self.lock:
            completed_ids = []
            
            for task_id, process in list(self.running_tasks.items()):
                if process.poll() is not None:  # Процес завершено
                    task = self.tasks.get(task_id)
                    if task:
                        if process.returncode == 0:
                            task.status = TaskStatus.COMPLETED
                            task.completed_at = datetime.now().isoformat()
                            task.progress = 100
                            # Шукаємо результат в Inbox
                            task.result_path = self._find_result_file(task)
                        else:
                            task.status = TaskStatus.FAILED
                            # Читаємо stderr для деталей помилки
                            try:
                                stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                                stdout_output = process.stdout.read().decode('utf-8', errors='ignore')
                                
                                error_msg = f"Process exited with code {process.returncode}"
                                if stderr_output:
                                    error_msg += f"\n\nSTDERR:\n{stderr_output[:500]}"
                                if stdout_output:
                                    error_msg += f"\n\nSTDOUT:\n{stdout_output[:500]}"
                                
                                task.error = error_msg
                                print(f"❌ [QUEUE] Помилка задачі {task_id[:8]}...:\n{error_msg}")
                            except Exception as e:
                                task.error = f"Process exited with code {process.returncode}. Error reading output: {e}"
                            
                            task.completed_at = datetime.now().isoformat()
                        
                        self._notify_status_change(task_id)
                    
                    completed_ids.append(task_id)
            
            # Видаляємо завершені процеси
            for task_id in completed_ids:
                del self.running_tasks[task_id]
            
            if completed_ids:
                self._save_state()
    
    def _start_pending_tasks(self):
        """Запускає задачі з черги, якщо є вільні слоти"""
        # Перевіряємо, скільки задач виконується
        running_count = len(self.running_tasks)
        
        if running_count >= self.max_parallel:
            return  # Немає вільних слотів
        
        # Отримуємо задачі в черзі, відсортовані за пріоритетом
        pending_tasks = sorted(
            self.get_pending_tasks(),
            key=lambda t: (-t.priority, t.created_at)
        )
        
        # Запускаємо задачі до заповнення слотів
        for task in pending_tasks[:self.max_parallel - running_count]:
            self._start_task(task)
    
    def _start_task(self, task: AgentTask):
        """
        Запускає задачу.
        
        Args:
            task: Задача для запуску
        """
        try:
            # Визначаємо команду залежно від типу агента
            agent_path = root_dir / "agents" / f"{task.agent_type}_agent.py"
            
            if not agent_path.exists():
                task.status = TaskStatus.FAILED
                task.error = f"Agent file not found: {agent_path}"
                return
            
            # Формуємо команду
            cmd = ["python", str(agent_path)]
            
            if task.agent_type == "writer":
                cmd.extend([task.topic or "", "--context", task.context, "--type", task.task_type])
            elif task.agent_type == "smm":
                cmd.extend([task.topic or "", "--context", task.context])
            elif task.agent_type == "coder":
                cmd.extend([task.project_name or "SystemCOO", "--task", task.task_type])
                if task.context:
                    cmd.extend(["--context", task.context])
            
            # Запускаємо процес з правильним кодуванням для Windows
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            
            process = subprocess.Popen(
                cmd,
                cwd=str(root_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True,
                encoding='utf-8',
                errors='replace'
            )
            
            # Оновлюємо статус
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.now().isoformat()
            task.progress = 10  # Початок виконання
            
            with self.lock:
                self.running_tasks[task.id] = process
                self._save_state()
            
            print(f"🚀 [QUEUE MANAGER] Запущено задачу: {task.id}")
            self._notify_status_change(task.id)
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            print(f"❌ [QUEUE MANAGER] Помилка запуску задачі {task.id}: {e}")
            self._notify_status_change(task.id)
    
    def _find_result_file(self, task: AgentTask) -> Optional[str]:
        """
        Шукає файл результату в папці Inbox.
        
        Args:
            task: Завершена задача
            
        Returns:
            Шлях до файлу результату або None
        """
        inbox_dir = root_dir / "memories" / "Inbox"
        code_analysis_dir = root_dir / "memories" / "CodeAnalysis"
        
        # Шукаємо файли, створені після початку задачі
        if task.started_at:
            start_time = datetime.fromisoformat(task.started_at)
            
            # Перевіряємо Inbox
            if inbox_dir.exists():
                for file in inbox_dir.glob("*_DONE_*.txt"):
                    if file.stat().st_mtime >= start_time.timestamp():
                        # Перевіряємо, чи файл відповідає задачі
                        if self._file_matches_task(file, task):
                            return str(file)
            
            # Перевіряємо CodeAnalysis
            if code_analysis_dir.exists():
                for file in code_analysis_dir.glob("*_DONE_*.txt"):
                    if file.stat().st_mtime >= start_time.timestamp():
                        if self._file_matches_task(file, task):
                            return str(file)
        
        return None
    
    def _file_matches_task(self, file: Path, task: AgentTask) -> bool:
        """
        Перевіряє, чи файл відповідає задачі.
        
        Args:
            file: Файл результату
            task: Задача
            
        Returns:
            True якщо файл відповідає задачі
        """
        filename = file.stem.lower()
        
        if task.agent_type == "writer":
            return "article" in filename or "referat" in filename or "coursework" in filename or "diploma" in filename
        elif task.agent_type == "smm":
            return "post" in filename
        elif task.agent_type == "coder":
            return task.task_type.lower() in filename
        
        return False
    
    def _notify_status_change(self, task_id: str):
        """Сповіщає про зміну статусу задачі"""
        task = self.tasks.get(task_id)
        if task:
            for callback in self.status_callbacks:
                try:
                    callback(task_id, task)
                except Exception as e:
                    print(f"⚠️ [QUEUE MANAGER] Помилка callback: {e}")
    
    def _save_state(self):
        """Зберігає стан черги"""
        try:
            state_file = self.state_dir / "queue_state.json"
            state = {
                "tasks": {tid: asdict(task) for tid, task in self.tasks.items()},
                "last_updated": datetime.now().isoformat()
            }
            
            # Конвертуємо TaskStatus в рядок для JSON
            for task_dict in state["tasks"].values():
                if isinstance(task_dict.get("status"), TaskStatus):
                    task_dict["status"] = task_dict["status"].value
            
            with open(state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [QUEUE MANAGER] Помилка збереження стану: {e}")
    
    def _load_state(self):
        """Завантажує збережений стан"""
        try:
            state_file = self.state_dir / "queue_state.json"
            if state_file.exists():
                with open(state_file, "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                # Відновлюємо задачі
                for tid, task_dict in state.get("tasks", {}).items():
                    # Конвертуємо статус з рядка в TaskStatus
                    if isinstance(task_dict.get("status"), str):
                        task_dict["status"] = TaskStatus(task_dict["status"])
                    
                    task = AgentTask(**task_dict)
                    # Тільки відновлюємо завершені задачі (не запускаємо їх знову)
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        self.tasks[tid] = task
        except Exception as e:
            print(f"⚠️ [QUEUE MANAGER] Помилка завантаження стану: {e}")
    
    def stop(self):
        """Зупиняє менеджер черги"""
        self.is_running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5)
        print("⏹️ [QUEUE MANAGER] Зупинено")


# Глобальний екземпляр менеджера
_queue_manager: Optional[AgentQueueManager] = None


def get_queue_manager() -> AgentQueueManager:
    """Отримує глобальний екземпляр менеджера черги"""
    global _queue_manager
    if _queue_manager is None:
        _queue_manager = AgentQueueManager()
    return _queue_manager

