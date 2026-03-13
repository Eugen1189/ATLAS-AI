import os
from abc import ABC, abstractmethod
from core.brain.blueprints import BlueprintManager

from core.brain.memory import memory_manager

class BaseBrain(ABC):
    """Abstract base class for AI brain backends."""
    
    def __init__(self):
        self.bp_manager = None
        self.memory = None

    def initialize(self, available_tools: list, tool_index: dict = None):
        """Common initialization for all brains."""
        self.tool_index = tool_index or {}
        self.bp_manager = BlueprintManager()
        self.bp_manager.load_blueprint(os.getenv("AXIS_BLUEPRINT", "default"))
        self.memory = memory_manager

        # --- Initialize RAG ---
        if self.memory.rag and self.memory.rag.is_available:
            self.memory.rag.ensure_indexed()
        
        return True

    @abstractmethod
    def think(self, user_input: str) -> str:
        """Process user input and return a response."""
        pass
