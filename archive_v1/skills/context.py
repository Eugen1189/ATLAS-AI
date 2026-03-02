"""
Спільний контекст для всіх департаментів ATLAS.

Цей клас зберігає стан системи та надає доступ до спільних ресурсів.
"""

from collections import deque
from typing import Optional


class Context:
    """
    Спільний контекст для всіх департаментів.
    
    Зберігає:
    - Активний проект
    - Останні дії (короткострокова пам'ять)
    - Стан системи
    - Посилання на департаменти
    """
    
    def __init__(self):
        """Ініціалізація контексту"""
        # Короткострокова пам'ять (замість memory.py)
        self.active_project: Optional[str] = None
        self.action_log = deque(maxlen=3)  # Останні 3 дії

        # Стан системи (використовується департаментами для передачі статусу)
        self.system_state: dict = {}

        # Посилання на департаменти (будуть встановлені після ініціалізації)
        self.vision_dept = None      # Vision Department
        self.operations_dept = None  # Operations Department

        print("✅ [CONTEXT] Контекст ініціалізовано")

    def get_system_state(self, key: str, default=None):
        """Повертає значення стану системи за ключем"""
        return self.system_state.get(key, default)

    def set_system_state(self, key: str, value):
        """Встановлює значення стану системи"""
        self.system_state[key] = value
        print(f"🔧 [CONTEXT] Стан системи: {key} = {value}")
    
    def get_active_project(self) -> Optional[str]:
        """Повертає назву активного проекту"""
        return self.active_project
    
    def set_active_project(self, project_name: str):
        """Встановлює активний проект"""
        self.active_project = project_name
        print(f"📁 [CONTEXT] Активний проект: {project_name}")
    
    def log_action(self, action: str):
        """
        Додає дію в лог (короткострокова пам'ять).
        
        Args:
            action: Опис дії
        """
        self.action_log.append(action)
        print(f"📝 [CONTEXT] Додано дію: {action}")
    
    def get_recent_actions(self, limit: int = 3) -> list:
        """
        Повертає останні дії.
        
        Args:
            limit: Кількість дій для повернення
            
        Returns:
            Список останніх дій
        """
        return list(self.action_log)[-limit:]
    
    def __repr__(self):
        return f"<Context: project={self.active_project}, actions={len(self.action_log)}>"



