"""
Scenario Manager - менеджер сценаріїв для автоматизації послідовностей команд

Простий клас, який бере назву сценарію і віддає список команд.
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Optional
import time
from skills.system_navigator import SystemNavigator
from skills.morning_routine import run_dev_morning
from skills.launcher import Launcher


class ScenarioManager:
    """
    Менеджер сценаріїв для автоматизації послідовностей команд.
    
    Читає сценарії з config/scenarios.json та повертає список команд.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Ініціалізація Scenario Manager.
        """
        if config_path is None:
            import config
            config_path = str(config.SCENARIOS_CONFIG_PATH)
        
        self.config_path = config_path
        self.scenarios = self._load_scenarios()
        self.navigator = SystemNavigator()
        self.launcher = Launcher()
        
        print(f"✅ [SCENARIO] Завантажено {len(self.scenarios)} сценаріїв")
    
    def _load_scenarios(self) -> Dict:
        """Завантажує сценарії з JSON файлу."""
        if not os.path.exists(self.config_path):
            print(f"⚠️ [SCENARIO] Файл {self.config_path} не знайдено")
            return {}
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                scenarios = json.load(f)
                return scenarios
        except Exception as e:
            print(f"❌ [SCENARIO] Помилка завантаження: {e}")
            return {}
    
    def get_scenario(self, scenario_name: str) -> Optional[List[str]]:
        """Повертає список команд для сценарію."""
        if scenario_name in self.scenarios:
            return self.scenarios[scenario_name].get("steps", [])
        return None
    
    def get_success_message(self, scenario_name: str) -> str:
        """Повертає повідомлення про успіх для сценарію."""
        if scenario_name in self.scenarios:
            return self.scenarios[scenario_name].get("success_message", "Сценарій виконано.")
        return "Готово."
    
    def list_available_scenarios(self) -> str:
        """Повертає список доступних сценаріїв."""
        return ", ".join(self.scenarios.keys())
    
    def is_scenario_request(self, query: str) -> bool:
        """Перевіряє, чи запит стосується сценарію (тільки точні тригери)."""
        query_lower = query.lower()
        
        # Ми залишаємо тут тільки технічні тригери. 
        # Розмовні тригери тепер обробляються через Brain -> Tools.
        scenario_keywords = [
            "gaming mode", "ігровий режим",
            "focus mode", "режим фокусу", 
            "emergency cleanup", "екстрене очищення",
            "ранковий протокол"
        ]
        
        return any(kw in query_lower for kw in scenario_keywords)
    
    def execute_scenario(self, query: str, shell_executor, atlas_core=None) -> Optional[str]:
        """Виконує сценарій на основі запиту."""
        query_lower = query.lower()
        
        if "ранковий протокол" in query_lower or "morning protocol" in query_lower:
            run_dev_morning()
            return "Ранковий протокол активовано. Систему очищено, проекти відкрито."

        # Визначаємо назву сценарію
        scenario_name = None
        scenario_keywords = {
            "gaming_mode": ["ігровий режим", "gaming mode"],
            "focus_mode": ["режим фокусу", "focus mode"],
            "emergency_cleanup": ["emergency cleanup", "екстрене очищення"]
        }
        
        for name, keywords in scenario_keywords.items():
            if any(kw in query_lower for kw in keywords):
                scenario_name = name
                break
        
        if not scenario_name:
            return None
            
        steps = self.get_scenario(scenario_name)
        if not steps:
            return None
        
        # Виконуємо кожен крок
        for i, step in enumerate(steps, 1):
            shell_executor.execute(step)
            
        return self.get_success_message(scenario_name)

    def open_workspace(self, project_name):
        """Розгортає робочий простір для проекту"""
        path = self.launcher.find_project_globally(project_name)
        if path:
            print(f"🚀 [WORKSPACE] Opening: {path}")
            os.startfile(path)
            # Запускаємо Cursor
            os.system(f'cursor "{path}"')
            # Відкриваємо Perplexity
            os.system('start https://www.perplexity.ai/search?q=ai+updates+2026')
            return f"Сер, робочий простір для проекту {project_name} розгорнуто. Я готовий до роботи!"
        return f"Вибачте, але я не зміг знайти проект '{project_name}' на вашому диску."
