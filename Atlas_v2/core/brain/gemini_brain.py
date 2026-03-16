import os
import google.generativeai as genai
from .base import BaseBrain


class GeminiBrain(BaseBrain):
    """Brain implementation using Google Gemini 2.0 Flash."""
    
    def __init__(self):
        self.model = None
        self.chat_session = None

    def initialize(self, available_tools: list, tool_index: dict = None):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return False
            
        # Use shared initialization logic
        super().initialize(available_tools, tool_index=tool_index)

        genai.configure(api_key=api_key)
        
        system_instr = self.bp_manager.get_system_prompt_addon() + self.memory.get_context_for_prompt()
        system_instr += "\n[IMMEDIATE FEEDBACK RULE]: If a tool you require is not available in the current context, IMMEDIATELY notify the user and suggest an incremental_scan. DO NOT create a plan to call a missing tool."

        # Level 2: Guardrail Configuration (v3.1.0)
        generation_config = {
            "temperature": 0.1,  # Low creativity for precise tool logic
            "top_p": 0.95,
            "max_output_tokens": 8192, # Increased to prevent JSON truncation for large projects
            "response_mime_type": "application/json"
        }

        self.model = genai.GenerativeModel(
            model_name='gemini-2.0-flash',
            tools=available_tools if available_tools else None,
            system_instruction=system_instr,
            generation_config=generation_config
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
