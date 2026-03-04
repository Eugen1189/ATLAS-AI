import os
import importlib
import sys
from abc import ABC, abstractmethod
from pathlib import Path
import google.generativeai as genai
from core.i18n import lang

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

class GeminiBrain(BaseBrain):
    """Brain implementation using Google Gemini 2.0 Flash."""
    
    def __init__(self):
        self.model = None
        self.chat_session = None

    def initialize(self, available_tools: list):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # We don't raise here but wait for AxisCore to handle it if this brain is selected
            return False
            
        genai.configure(api_key=api_key)
        
        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=available_tools if available_tools else None
        )
        
        # Create a chat session with automatic function calling
        self.chat_session = self.model.start_chat(
            history=[], 
            enable_automatic_function_calling=True
        )
        return True

    def think(self, user_input: str) -> str:
        if not self.chat_session:
            return "Gemini Brain not initialized."
        response = self.chat_session.send_message(user_input)
        return response.text

class OllamaBrain(BaseBrain):
    """
    Brain implementation using local Ollama.
    (Phase 2: Local-First Core)
    """
    
    def __init__(self):
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.available_tools = []

    def initialize(self, available_tools: list):
        self.available_tools = available_tools
        # For now, we just log that we are using Ollama
        print(f"🦙 [Ollama Brain] Initialized with model: {self.model_name}")
        # Note: Local tool calling implementation will be added in Phase 2 step 2
        return True

    def think(self, user_input: str) -> str:
        # Placeholder for Ollama API call
        return f"[Ollama {self.model_name}]: I am running locally, but tool execution is still being implemented in V3.0-alpha."

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
