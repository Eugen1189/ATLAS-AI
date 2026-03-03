import os
import json
from dotenv import load_dotenv

# Find .env file starting precisely from this directory, moving up
current_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.abspath(os.path.join(current_dir, "..", "..", ".env"))
load_dotenv(dotenv_path=env_path)

class LangModule:
    """Singleton module to handle i18n localization in AXIS."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(LangModule, cls).__new__(cls)
            cls._instance._init_lang()
        return cls._instance
        
    def _init_lang(self):
        # Default language is English. Users can overwrite it with set LANGUAGE=uk in .env
        self.language = os.getenv("LANGUAGE", "en").lower()
        self.texts = {}
        
        # Determine locales folder path
        self.locales_dir = os.path.abspath(os.path.join(current_dir, "..", "config", "locales"))
        
        # Load the selected language dictionary
        file_path = os.path.join(self.locales_dir, f"{self.language}.json")
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                self.texts = json.load(file)
        except Exception as e:
            print(f"⚠️ [i18n] Failed to load locale '{self.language}' at {file_path}. Falling back to 'en'. Error: {e}")
            try:
                # Fallback to English
                with open(os.path.join(self.locales_dir, "en.json"), "r", encoding="utf-8") as fb_file:
                    self.texts = json.load(fb_file)
            except Exception as e2:
                print(f"❌ [i18n] Critical error! English locale missing as well: {e2}")
                self.texts = {}
                
    def get(self, key: str, **kwargs) -> str:
        """
        Retrieves a translated string using dot notation (e.g., 'system.welcome').
        Formats the string using any kwargs provided.
        Falls back to returning the key if the translation is missing.
        """
        keys = key.split('.')
        val = self.texts
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return key # Missing key fallback
        
        if isinstance(val, str):
            try:
                return val.format(**kwargs)
            except KeyError as e:
                # Formatting error or missing kwarg
                return val + f" [fmt error: {e}]"
        return str(val)

# Global instance for ease of use across the application
lang = LangModule()
