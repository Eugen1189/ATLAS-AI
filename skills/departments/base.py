"""
Базовий клас для всіх департаментів ATLAS.

Кожен департамент наслідується від цього класу і реалізує
методи can_handle() та handle().
"""

from abc import ABC, abstractmethod


class Department(ABC):
    """
    Базовий клас для всіх департаментів.
    
    Кожен департамент:
    - Має унікальні тригери для розпізнавання команд
    - Має пріоритет (чим менше, тим вище)
    - Реалізує can_handle() для перевірки, чи може обробити запит
    - Реалізує handle() для обробки запиту
    """
    
    def __init__(self, name: str, priority: int = 5):
        """
        Ініціалізація департаменту.
        
        Args:
            name: Назва департаменту (для логування)
            priority: Пріоритет (1 = найвищий, 10 = найнижчий)
        """
        self.name = name
        self.priority = priority
        self.triggers = []  # Список тригерів для розпізнавання
        print(f"✅ [DEPARTMENT] Ініціалізовано: {self.name} (пріоритет: {priority})")
    
    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """
        Перевіряє, чи може департамент обробити запит.
        
        Args:
            query: Нормалізований запит користувача
            
        Returns:
            True, якщо департамент може обробити запит
        """
        pass
    
    @abstractmethod
    def handle(self, query: str, context=None) -> str:
        """
        Обробляє запит і повертає результат.
        
        Args:
            query: Нормалізований запит користувача
            context: Спільний контекст (Context об'єкт)
            
        Returns:
            Результат обробки (рядок) або None, якщо не оброблено
        """
        pass
    
    def __repr__(self):
        return f"<Department: {self.name}, priority={self.priority}>"



