import os
from .base import BaseBrain
class BrainFactory:
    """Factory to create the appropriate brain based on configuration."""
    
    @staticmethod
    def create_brain() -> BaseBrain:
        brain_type = os.getenv("AI_BRAIN", "gemini").lower()
        
        if brain_type == "ollama":
            from .ollama_brain import OllamaBrain
            return OllamaBrain()
        elif brain_type == "gemini":
            from .gemini_brain import GeminiBrain
            return GeminiBrain()
        else:
            from .gemini_brain import GeminiBrain
            print(f"⚠️ Unknown brain type '{brain_type}', falling back to Gemini.")
            return GeminiBrain()

