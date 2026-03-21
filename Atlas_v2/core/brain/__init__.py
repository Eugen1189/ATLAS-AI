import os
from .base import BaseBrain
from .gemini_brain import GeminiBrain
from .ollama_brain import OllamaBrain

class BrainFactory:
    """Factory to create the appropriate brain based on configuration."""
    
    @staticmethod
    def create_brain() -> BaseBrain:
        brain_type = os.getenv("AI_BRAIN", "gemini").lower()
        
        if brain_type == "ollama":
            return OllamaBrain()
        elif brain_type == "gemini":
            return GeminiBrain()
        else:
            print(f"⚠️ Unknown brain type '{brain_type}', falling back to Gemini.")
            return GeminiBrain()

