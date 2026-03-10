from abc import ABC, abstractmethod

class BaseBrain(ABC):
    """Abstract base class for AI brain backends."""
    
    @abstractmethod
    def initialize(self, available_tools: list):
        """Initialize the AI model with available tools."""
        pass

    @abstractmethod
    def think(self, user_input: str) -> str:
        """Process user input and return a response."""
        pass
