import google.generativeai as genai
import os
import importlib
import sys
from pathlib import Path
from dotenv import load_dotenv
from core.i18n import lang

# 1. Get the absolute path to the folder where this script resides (Atlas_v2/core)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Go up two levels (Atlas_v2/core -> Atlas_v2 -> SystemCOO) to find .env
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))

# 3. Load keys using absolute path
load_dotenv(dotenv_path=env_path)

class AtlasCore:
    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(lang.get("system.missing_gemini_key", path=env_path))
            
        genai.configure(api_key=api_key)
        
        # Load tools
        self.available_tools = self._load_skills()
        
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=self.available_tools if self.available_tools else None
        )
        
        # Create a chat session. This is our "Short-term memory"
        # enable_automatic_function_calling=True allows Gemini to call functions autonomously
        self.chat_session = self.model.start_chat(history=[], enable_automatic_function_calling=True)
        
        print(lang.get("system.core_init_success", count=len(self.available_tools)))

    def _load_skills(self):
        """Scans the agent_skills folder and loads EXPORTED_TOOLS from each skill's manifest.py."""
        tools = []
        skills_dir = Path(__file__).parent.parent / "agent_skills"
        
        # Add Atlas_v2 to sys.path for correct imports
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
                        print(lang.get("system.skill_loaded", name=skill_folder.name))
                except Exception as e:
                    print(lang.get("system.skill_load_error", name=skill_folder.name, error=e))
        
        return tools

    def think(self, user_input: str) -> str:
        # Send message to the session
        response = self.chat_session.send_message(user_input)
        return response.text
