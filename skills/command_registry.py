"""
Command Registry - надійна система розпізнавання команд

Використовує regex patterns для детерміністичного розпізнавання команд
без залежності від AI для базового парсингу.

Структура команди:
- patterns: список regex patterns для розпізнавання
- department: назва департаменту для обробки
- priority: пріоритет (1 = найвищий)
- handler: (опціонально) назва методу для виклику замість handle
- args_extractor: (опціонально) функція для витягування аргументів з запиту
"""

import re
from typing import Dict, List, Optional, Tuple

# Структура команди
CommandDefinition = Dict[str, any]

# Реєстр команд з пріоритетами (1 = найвищий)
COMMAND_REGISTRY: Dict[str, CommandDefinition] = {
    # === SYSTEM STATUS & REFLEXES (Operations) ===
    "get_status": {
        "patterns": [
            r"\bстатус\b", r"\bдіагностика\b", r"\bяк ти\b", 
            r"\bстатус системи\b", r"\bсистема\b", r"\bнавантаження\b"
        ],
        "department": "Operations",
        "priority": 1,
        "handler": "handle" # Default handle
    },
    


    "stabilize_system": {
        "patterns": [r"\bстабілізація\b", r"\bстабілізуй\b", r"\bочисти память\b", r"\bоптимізуй\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "handle"
    },
    
    # === APP LAUNCHING (Operations) ===
    "open_cursor": {
        "patterns": [r"\bвідкрий\s+курсор\b", r"\bзапусти\s+курсор\b", r"\bкурсор\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "open_app_wrapper",
        "args_extractor": lambda q: ["cursor"]
    },
    
    "open_chrome": {
        "patterns": [r"\bвідкрий\s+хром\b", r"\bвідкрий\s+браузер\b", r"\bзапусти\s+хром\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "open_app_wrapper",
        "args_extractor": lambda q: ["chrome"]
    },
    
    "open_telegram": {
        "patterns": [r"\bвідкрий\s+телеграм\b", r"\bзапусти\s+телеграм\b", r"\bтелеграм\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "open_app_wrapper",
        "args_extractor": lambda q: ["telegram"]
    },

    "open_youtube": {
        "patterns": [r"\bютуб\b", r"\byoutube\b", r"\bвідкрий ютуб\b", r"\bзапусти ютуб\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "open_app_wrapper",
        "args_extractor": lambda q: ["https://youtube.com"]
    },

    "open_notepad": {
        "patterns": [r"\bвідкрий блокнот\b", r"\bзапусти блокнот\b", r"\bблокнот\b", r"\bnotepad\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "open_app_wrapper",
        "args_extractor": lambda q: ["notepad"]
    },

    "open_calculator": {
        "patterns": [r"\bкалькулятор\b", r"\bвідкрий калькулятор\b", r"\bcalc\b", r"\bкальк\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "open_app_wrapper",
        "args_extractor": lambda q: ["calc"]
    },

    "open_music": {
        "patterns": [
            r"\bмузика\b", r"\bмюзік\b", r"\bspotify\b",
            r"\bвключи музику\b", r"\bграй музику\b", r"\bзапусти музику\b",
            r"\bplay music\b", r"\bвідкрий музику\b"
        ],
        "department": "Operations",
        "priority": 1,
        "handler": "handle"
    },

    "stop_music_cmd": {
        "patterns": [
            r"\bзупини музику\b", r"\bстоп музика\b", r"\bвимкни музику\b",
            r"\bstop music\b", r"\bпауза музик\b"
        ],
        "department": "Operations",
        "priority": 1,
        "handler": "stop_music_wrapper",
        "args_extractor": lambda q: []
    },
    
    # === PROTOCOLS (Operations) ===
    "morning_protocol": {
        "patterns": [r"\bранковий протокол\b", r"\bранковий\b", r"\bпротокол\b"],
        "department": "Operations",
        "priority": 1,
        "handler": "handle"
    },
    
    # === VISION (Vision) ===
    "take_screenshot": {
        "patterns": [r"\bскріншот\b", r"\bскрін\b", r"\bscreenshot\b", r"\bзнімок екрану\b"],
        "department": "Vision",
        "priority": 1,
        "handler": "_take_screenshot_wrapper",
        "args_extractor": lambda q: []
    },

    "scan_system": {
        "patterns": [r"\bскануй систему\b", r"\bсканування\b", r"\bдіагностика візуальна\b"],
        "department": "Vision",
        "priority": 1,
        "handler": "handle"
    },

    # === VISION CONTROL (Vision) ===
    "vision_start": {
        "patterns": [
            r"start\s+vision", r"enable\s+camera", r"active\s+vision",
            r"запусти\s+камеру", r"увімкни\s+зір", r"камера\s+старт",
            r"zapuste\s+kameru", r"zapusty\s+kameru", r"vision\s+on",
            r"включи\s+камеру", r"включи\s+зір",
            r"активуй\s+зір", r"активуй\s+камеру", r"запусти\s+зір",
            r"увімкни\s+камеру", r"\bзір\s+увімкни\b", r"\bкамеру\s+увімкни\b"
        ],
        "department": "Vision",
        "priority": 1,
        "handler": "start"
    },

    "vision_stop": {
        "patterns": [
            r"stop\s+vision", r"disable\s+camera", r"vision\s+off",
            r"зупини\s+камеру", r"вимкни\s+зір", r"камера\s+стоп",
            r"zupyny\s+kameru", r"вимкни\s+камеру",
            r"вимкни\s+зір", r"зупини\s+зір", r"деактивуй\s+зір"
        ],
        "department": "Vision",
        "priority": 1,
        "handler": "stop"
    },
    
    # === WEB SEARCH (Operations) ===
    "web_search": {
        "patterns": [
            r"\bзнайди\b", r"\bпошук\b", r"\bгугл\b", r"\bgoogle\b", 
            r"\bпошукай\b", r"\bsearch\b", r"\bв\s+інтернеті\b"
        ],
        "department": "Operations",
        "priority": 2, # Lower priority than direct app launch
        "handler": "handle"
    },
    
    # === SYSTEM NAVIGATOR (Operations) ===
    "visual_click": {
        "patterns": [
            r"клікни\s+на\s+(?P<target>.+)", 
            r"натисни\s+на\s+(?P<target>.+)",
            r"click\s+(?P<target>.+)",
            r"знайди\s+і\s+клікни\s+(?P<target>.+)"
        ],
        "department": "Operations",
        "priority": 1,
        "handler": "handle_visual_click", # New handler in Operations
        "args_extractor": lambda q: [re.search(r"(на|click|клікни)\s+(?P<target>.+)", q, re.IGNORECASE).group("target")]
    },
    
    "type_text": {
        "patterns": [
            r"напиши\s+(?P<text>.+)",
            r"надрукуй\s+(?P<text>.+)",
            r"введи\s+(?P<text>.+)",
            r"type\s+(?P<text>.+)"
        ],
        "department": "Operations",
        "priority": 1,
        "handler": "handle_type_text", # New handler
        "args_extractor": lambda q: [re.search(r"(напиши|надрукуй|введи|type)\s+(?P<text>.+)", q, re.IGNORECASE).group("text")]
    },
    
    "save_file": {
        "patterns": [r"збережи\s+файл", r"зберегти", r"сейв", r"натисни\s+зберегти"],
        "department": "Operations",
        "priority": 1,
        "handler": "handle_press_key",
        "args_extractor": lambda q: ["ctrl+s"]
    }
}


class CommandRegistry:
    """
    Реєстр команд для надійного розпізнавання.
    """
    
    def __init__(self):
        """Ініціалізація реєстру"""
        self.commands = COMMAND_REGISTRY
        # Компілюємо regex patterns для швидшого пошуку
        self.compiled_patterns = {}
        for cmd_name, cmd_def in self.commands.items():
            self.compiled_patterns[cmd_name] = [
                re.compile(pattern, re.IGNORECASE) 
                for pattern in cmd_def["patterns"]
            ]
    
    def find_command(self, query: str) -> Optional[Tuple[str, CommandDefinition]]:
        """
        Знаходить команду в запиті.
        
        Args:
            query: Запит користувача
            
        Returns:
            Tuple (command_name, command_definition) або None
        """
        query_lower = query.lower()
        
        # Перевіряємо команди за пріоритетом
        sorted_commands = sorted(
            self.commands.items(),
            key=lambda x: x[1].get("priority", 999)
        )
        
        
        for cmd_name, cmd_def in sorted_commands:
            # Check compiled patterns
            if cmd_name in self.compiled_patterns:
                for pattern in self.compiled_patterns[cmd_name]:
                    if pattern.search(query_lower):
                        # print(f"✅ [REGISTRY] Matched: {cmd_name}")
                        return (cmd_name, cmd_def)
            else:
                 # Fallback if not compiled
                 for pat_str in cmd_def["patterns"]:
                     if re.search(pat_str, query_lower, re.IGNORECASE):
                         return (cmd_name, cmd_def)
        
        return None
    
    def find_command_with_handler(self, query: str) -> Optional[Tuple[str, CommandDefinition, List[str]]]:
        """
        Знаходить команду з витягнутими аргументами для handler методу.
        
        Args:
            query: Запит користувача
            
        Returns:
            Tuple (command_name, command_definition, args_list) або None
        """
        result = self.find_command(query)
        if not result:
            return None
        
        cmd_name, cmd_def = result
        args = []
        
        # Helper to extract arguments using lambda
        if "args_extractor" in cmd_def and callable(cmd_def["args_extractor"]):
            try:
                extracted = cmd_def["args_extractor"](query)
                if isinstance(extracted, list):
                    args = extracted
                elif extracted is not None:
                    args = [extracted]
            except Exception as e:
                # print(f"⚠️ [REGISTRY] Arg extraction failed: {e}")
                pass
        
        return (cmd_name, cmd_def, args)
    
    def get_department_for_query(self, query: str) -> Optional[str]:
        """
        Повертає назву департаменту для запиту.
        
        Args:
            query: Запит користувача
            
        Returns:
            Назва департаменту або None
        """
        result = self.find_command(query)
        if result:
            _, cmd_def = result
            return cmd_def.get("department")
        return None

    @staticmethod
    def split_sequence(query: str) -> List[str]:
        """
        Розбиває запит на послідовність окремих команд.
        Використовує маркери: 'потім', 'після цього', '->', 'then', etc.
        """
        sequence_markers = [" потім ", " після цього ", " -> ", " а потім ", " after that ", " then ", " і потім "]
        
        # Перевіряємо, чи є хоча б один маркер у запиті
        query_lower = query.lower()
        if not any(m in query_lower for m in sequence_markers):
            return [query.strip()]
            
        # Складаємо regex патерн
        pattern = "|".join(map(re.escape, sequence_markers))
        
        # Розбиваємо
        steps = re.split(pattern, query, flags=re.IGNORECASE)
        
        # Очищаємо результати
        return [s.strip() for s in steps if s.strip()]


# Глобальний екземпляр
_registry_instance = None

def get_registry() -> CommandRegistry:
    """Повертає глобальний екземпляр CommandRegistry"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CommandRegistry()
    return _registry_instance
