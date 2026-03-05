import os
import yaml
from core.logger import logger

class BlueprintManager:
    """
    Manages AXIS personality blueprints and user preferences.
    """
    def __init__(self):
        # Path to blueprints directory (Atlas_v2/core/blueprints)
        self.blueprints_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "blueprints"
        ))
        os.makedirs(self.blueprints_dir, exist_ok=True)
        self.active_blueprint = {}

    def load_blueprint(self, name: str = "default") -> dict:
        """
        Loads a blueprint YAML file by name.
        
        Args:
            name (str): Name of the blueprint (filename without .yaml).
            
        Returns:
            dict: The loaded blueprint data.
        """
        file_path = os.path.join(self.blueprints_dir, f"{name}.yaml")
        
        if not os.path.exists(file_path):
            logger.warning("personality.blueprint_not_found", name=name)
            # Create default if it doesn't exist
            if name == "default":
                self._create_default_blueprint(file_path)
            else:
                return self.load_blueprint("default")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self.active_blueprint = yaml.safe_load(f)
                logger.info("personality.loaded", blueprint=name)
                return self.active_blueprint
        except Exception as e:
            logger.error("personality.load_error", name=name, error=str(e))
            return {}

    def _create_default_blueprint(self, path: str):
        """Creates the initial default personality blueprint."""
        default_data = {
            "name": "AXIS",
            "role": "Senior AI Collaborator",
            "style": "witty_and_precise",
            "hud_color": "#00FF00",
            "system_guidance": "You are a professional yet friendly AI architect. Use technical terms accurately."
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(default_data, f, default_flow_style=False)
            logger.info("personality.default_created", path=path)
        except Exception as e:
            logger.error("personality.setup_error", error=str(e))

    def get_system_prompt_addon(self) -> str:
        """
        Generates a system prompt snippet based on the active blueprint.
        """
        if not self.active_blueprint:
            return ""
            
        b = self.active_blueprint
        return (
            f"\n### IDENTITY & STYLE:\n"
            f"- **Name**: {b.get('name', 'AXIS')}\n"
            f"- **Role**: {b.get('role', 'AI Assistant')}\n"
            f"- **Style**: {b.get('style', 'neutral')}\n"
            f"- **Guidance**: {b.get('system_guidance', 'Be helpful.')}\n"
        )
