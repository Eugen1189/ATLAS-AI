import google.generativeai as genai
import os
import importlib
import sys
from pathlib import Path
from dotenv import load_dotenv

# 1. Отримуємо абсолютний шлях до папки, де лежить цей скрипт (Atlas_v2/core)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Піднімаємося на два рівні вгору (Atlas_v2/core -> Atlas_v2 -> SystemCOO), щоб знайти .env
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))

# 3. Завантажуємо ключі за абсолютним шляхом
load_dotenv(dotenv_path=env_path)

class AtlasCore:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(f"❌ GEMINI_API_KEY не знайдено! Перевірено шлях: {env_path}")
            
        genai.configure(api_key=api_key)
        
        # Завантажуємо інструменти
        self.available_tools = self._load_skills()
        
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=self.available_tools if self.available_tools else None
        )
        
        # Створюємо сесію чату. Це наша "Короткострокова пам'ять"
        # enable_automatic_function_calling=True дозволяє Gemini самому викликати функції
        self.chat_session = self.model.start_chat(history=[], enable_automatic_function_calling=True)
        
        print(f"🧠 [Atlas V2 Core]: Ініціалізація успішна. Завантажено {len(self.available_tools)} інструментів.")

    def _load_skills(self):
        """Сканує папку agent_skills та завантажує EXPORTED_TOOLS з manifest.py кожного скіла."""
        tools = []
        skills_dir = Path(__file__).parent.parent / "agent_skills"
        
        # Додаємо Atlas_v2 до sys.path для коректних імпортів
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        if not skills_dir.exists():
            return tools

        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir() and (skill_folder / "manifest.py").exists():
                try:
                    module_path = f"agent_skills.{skill_folder.name}.manifest"
                    module = importlib.import_module(module_path)
                    
                    if hasattr(module, "EXPORTED_TOOLS"):
                        tools.extend(module.EXPORTED_TOOLS)
                        print(f"✅ [Kernel]: Скіл '{skill_folder.name}' завантажено.")
                except Exception as e:
                    print(f"⚠️ [Kernel]: Помилка завантаження скіла '{skill_folder.name}': {e}")
        
        return tools

    def think(self, user_input: str) -> str:
        # Відправляємо повідомлення в сесію
        response = self.chat_session.send_message(user_input)
        return response.text
