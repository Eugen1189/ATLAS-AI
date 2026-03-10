import os
import google.generativeai as genai
from core.brain.blueprints import BlueprintManager
from core.brain.memory import memory_manager
from .base import BaseBrain

class GeminiBrain(BaseBrain):
    """Brain implementation using Google Gemini 2.0 Flash."""
    
    def __init__(self):
        self.model = None
        self.chat_session = None

    def initialize(self, available_tools: list):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False
            
        self.bp_manager = BlueprintManager()
        self.bp_manager.load_blueprint(os.getenv("AXIS_BLUEPRINT", "default"))
        self.memory = memory_manager

        # --- Initialize RAG ---
        if self.memory.rag and self.memory.rag.is_available:
            self.memory.rag.ensure_indexed()

        genai.configure(api_key=api_key)
        
        system_instr = self.bp_manager.get_system_prompt_addon() + self.memory.get_context_for_prompt()

        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=available_tools if available_tools else None,
            system_instruction=system_instr
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

        # --- RAG: Enrich query with relevant context ---
        enriched_input = user_input
        if self.memory.rag and self.memory.rag.is_available:
            rag_context = self.memory.rag.get_context_block(user_input, n_results=5)
            if rag_context:
                enriched_input = f"{rag_context}\n\nUser question: {user_input}"

        response = self.chat_session.send_message(enriched_input)
        return response.text
