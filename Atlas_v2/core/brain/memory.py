import os
import json
from datetime import datetime
from core.logger import logger

class MemoryManager:
    """
    Manages the long-term project context and facts for AXIS.
    Prevents 'Amnesia' by storing and retrieving key project metadata.
    """
    def __init__(self):
        # Path: Atlas_v2/../memories/facts.json
        self.memories_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "memories"
        ))
        os.makedirs(self.memories_dir, exist_ok=True)
        self.facts_file = os.path.join(self.memories_dir, "facts.json")
        self.facts = self._load_facts()

    def _load_facts(self) -> dict:
        """Loads facts from JSON file."""
        if not os.path.exists(self.facts_file):
            return {}
        try:
            with open(self.facts_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error("memory.load_error", error=str(e))
            return {}

    def store_fact(self, key: str, value: str):
        """
        Stores a fact in the long-term context.
        
        Args:
            key (str): Fact identifier (e.g., 'skill_weather_path').
            value (str): The fact content.
        """
        self.facts[key] = {
            "value": value,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self._save_facts()
        logger.info("memory.fact_stored", key=key)

    def _save_facts(self):
        """Saves facts to JSON file."""
        try:
            with open(self.facts_file, "w", encoding="utf-8") as f:
                json.dump(self.facts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("memory.save_error", error=str(e))

    def get_context_for_prompt(self, limit: int = 10) -> str:
        """
        Generates a text block of known facts for the system prompt.
        
        Args:
            limit (int): Number of most recent facts to include.
            
        Returns:
            str: Markdown formatted block of facts.
        """
        if not self.facts:
            return ""
            
        # Sort by timestamp descending
        sorted_facts = sorted(
            self.facts.items(), 
            key=lambda x: x[1].get("timestamp", ""), 
            reverse=True
        )[:limit]
        
        block = "\n### KNOWN PROJECT FACTS:\n"
        for key, data in sorted_facts:
            block += f"- [{key}]: {data['value']} (recorded: {data['timestamp']})\n"
        
        return block

# Global instance for core systems
memory_manager = MemoryManager()
