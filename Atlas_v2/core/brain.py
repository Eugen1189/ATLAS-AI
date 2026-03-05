import os
from abc import ABC, abstractmethod
import google.generativeai as genai

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

import json
import inspect
from typing import get_type_hints
import traceback

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class OllamaBrain(BaseBrain):
    """
    Brain implementation using local Ollama.
    (Phase 2: Local-First Core)
    """
    
    def __init__(self):
        self.model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.available_tools = []
        self.tool_map = {}
        self.system_prompt = ""
        self.history = []
        if OLLAMA_AVAILABLE:
            self.client = ollama.Client(host=self.base_url)
        else:
            self.client = None

    def _build_tool_manifest(self, tools: list) -> str:
        """Converts Python callables into a Markdown specification for ReAct."""
        manifest = (
            "You are AXIS, a highly advanced local AI assistant. "
            "You have access to the following tools. "
            "To use a tool, output ONLY a valid JSON block inside ```json\n``` markers with two keys: 'tool_name' and 'arguments'. "
            "For example:\n"
            "```json\n"
            "{\n"
            "  \"tool_name\": \"google_research\",\n"
            "  \"arguments\": {\"query\": \"latest AI news\"}\n"
            "}\n"
            "```\n\n"
            "Available tools:\n"
        )
        
        for tool in tools:
            name = getattr(tool, '__name__', str(tool))
            self.tool_map[name] = tool
            
            doc = getattr(tool, '__doc__', '') or 'No description available.'
            doc_summary = doc.strip().split('\n')[0]
            
            try:
                sig = inspect.signature(tool)
                params = []
                for p_name, param in sig.parameters.items():
                    # Simplified type extraction
                    p_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        p_type = getattr(param.annotation, '__name__', str(param.annotation).replace('typing.', ''))
                    params.append(f"{p_name}: {p_type}")
                sig_str = ", ".join(params)
            except Exception:
                sig_str = "..."
                
            manifest += f"- {name}({sig_str}): {doc_summary}\n"
            
        return manifest

    def initialize(self, available_tools: list):
        if not OLLAMA_AVAILABLE:
            from core.logger import logger
            logger.error("ollama.missing", reason="ollama python package is not installed")
            return False

        self.available_tools = available_tools
        self.system_prompt = self._build_tool_manifest(available_tools)
        
        # We start the chat history with the system prompt
        self.history = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        from core.logger import logger
        logger.info("ollama.initialized", model=self.model_name, tools_count=len(self.tool_map))
        return True

    def think(self, user_input: str) -> str:
        if not self.client:
            return "[OLLAMA OFFLINE]: Processing disabled due to missing 'ollama' package."

        from core.logger import logger
        
        self.history.append({"role": "user", "content": user_input})
        
        # Max 3 consecutive tool calls to prevent infinite loops
        max_depth = 3
        depth = 0
        
        while depth < max_depth:
            depth += 1
            
            try:
                response = self.client.chat(
                    model=self.model_name,
                    messages=self.history
                )
            except Exception as e:
                logger.error("ollama.api_error", error=str(e))
                return f"[AXIS Error] Failed to generate response from Ollama: {e}"
                
            msg_content = response['message']['content']
            self.history.append({"role": "assistant", "content": msg_content})
            
            # Check if there is a JSON tool request
            if "```json" in msg_content and "```" in msg_content.split("```json", 1)[1]:
                json_str = msg_content.split("```json")[1].split("```")[0].strip()
                try:
                    req = json.loads(json_str)
                    tool_name = req.get("tool_name")
                    args = req.get("arguments", {})
                    
                    if tool_name in self.tool_map:
                        logger.info("ollama.executing_tool", tool=tool_name, args=args)
                        tool_func = self.tool_map[tool_name]
                        
                        try:
                            # Execute the standard python tool
                            result = tool_func(**args)
                            tool_result_str = f"Tool '{tool_name}' returned:\n{result}"
                        except Exception as e:
                            tool_result_str = f"Tool '{tool_name}' failed with error: {e}\n{traceback.format_exc()}"
                    else:
                        tool_result_str = f"Error: Tool '{tool_name}' is not recognized."
                        
                    # Feed the result back to Ollama
                    logger.debug("ollama.tool_result", tool=tool_name, result=str(tool_result_str)[:200])
                    self.history.append({"role": "user", "content": tool_result_str})
                    
                    # Loop back to let Ollama process the tool result
                    continue
                    
                except json.JSONDecodeError:
                    logger.warning("ollama.invalid_json", json=json_str)
                    self.history.append({"role": "user", "content": "Error: Invalid JSON format. Please try again."})
                    continue
            
            # If no tool called, return the response text
            return msg_content
            
        return "[AXIS Error]: Exceeded maximum tool call depth."

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
