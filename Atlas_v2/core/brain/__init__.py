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
            
        from core.brain.blueprints import BlueprintManager
        from core.brain.memory import memory_manager
        self.bp_manager = BlueprintManager()
        self.bp_manager.load_blueprint(os.getenv("AXIS_BLUEPRINT", "default"))
        self.memory = memory_manager

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
            "### CRITICAL ENVIRONMENT RULES:\n"
            "1. **Platform**: You are running in a Python 3.12 environment (AXIS V2.5).\n"
            "2. **Skill Architecture**: Every 'Skill' MUST be a Python module.\n"
            "   - Path: `agent_skills/{skill_name}/`\n"
            "   - Files: `__init__.py` (logic) and `manifest.py` (metadata).\n"
            "3. **Prohibition**: DO NOT create Bash, Shell, or Batch scripts.\n"
            "4. **Logging**: Use `structlog` in all generated Python code.\n"
            "5. **Output Format**: If you decide to create a skill, use the `write_file` tool.\n\n"
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

        from core.brain.blueprints import BlueprintManager
        from core.brain.memory import memory_manager
        self.bp_manager = BlueprintManager()
        self.bp_manager.load_blueprint(os.getenv("AXIS_BLUEPRINT", "default"))
        self.memory = memory_manager

        self.available_tools = available_tools
        self.system_prompt = self._build_tool_manifest(available_tools)
        
        # Add personality and project memory context to the system prompt
        self.system_prompt += self.bp_manager.get_system_prompt_addon()
        self.system_prompt += self.memory.get_context_for_prompt()
        
        # We start the chat history with the system prompt
        self.history = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        from core.logger import logger
        logger.info("ollama.initialized", 
                    model=self.model_name, 
                    tools_count=len(self.tool_map),
                    blueprint=self.bp_manager.active_blueprint.get("name"))
        return True

    def check_model_health(self) -> bool:
        """
        Checks if the configured Ollama server is accessible and if the required model is completely downloaded.
        
        Returns:
            bool: True if the model is ready, False otherwise.
        """
        from core.logger import logger
        
        if not self.client:
            logger.error("ollama.health_check_failed", reason="Ollama client is not initialized.")
            return False
            
        try:
            # Get list of all local models
            models_response = self.client.list()
            downloaded_models = [m.get("model", "") for m in models_response.get("models", [])]
            
            # Ollama models usually append a tag like ':latest'. We do a partial match check
            # or an exact check depending on string formats.
            model_exists = any(self.model_name in m for m in downloaded_models)
            
            if model_exists:
                logger.info("ollama.model_ready", model=self.model_name, status="OK")
                return True
            else:
                logger.warning("ollama.model_missing", model=self.model_name, action="Run 'ollama run <model_name>' first.")
                return False
                
        except Exception as e:
            logger.error("ollama.server_offline", error=str(e), suggestion="Ensure Ollama is running.")
            return False

    def think(self, user_input: str) -> str:
        if not self.client:
            return "[OLLAMA OFFLINE]: Processing disabled due to missing 'ollama' package."

        from core.logger import logger
        
        self.history.append({"role": "user", "content": user_input})
        
        # Max 7 consecutive tool calls to prevent infinite loops but allow multi-step tasks
        max_depth = 7
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
                    # Robust JSON repair for Ollama
                    # 1. Handle triple quotes
                    if '"""' in json_str:
                        json_str = json_str.replace('"""', '"')
                    
                    # 2. Attempt to fix common nested quote issues in "content" or "arguments"
                    # This is a greedy approach but often works for simple nested structures
                    import re
                    
                    # Try to parse; if it fails, try to escape inner quotes
                    try:
                        req = json.loads(json_str, strict=False)
                    except json.JSONDecodeError:
                        # Find "content": "..." and escape internal quotes
                        # This is risky but Ollama often fails here
                        match = re.search(r'("content"| "text")\s*:\s*"(.*)"\s*,\s*"', json_str, re.DOTALL)
                        if not match: # Try it as the last element
                             match = re.search(r'("content"| "text")\s*:\s*"(.*)"\s*}', json_str, re.DOTALL)
                        
                        if match:
                            inner_content = match.group(2)
                            escaped_content = inner_content.replace('"', '\\"')
                            json_str = json_str.replace(inner_content, escaped_content)
                        
                        req = json.loads(json_str, strict=False)
                    tool_name = req.get("tool_name")
                    args = req.get("arguments", {})
                    
                    if tool_name in self.tool_map:
                        logger.info("ollama.executing_tool", tool=tool_name, args=args)
                        tool_func = self.tool_map[tool_name]
                        
                        try:
                            # Execute the standard python tool
                            result = tool_func(**args)
                            tool_result_str = f"Tool '{tool_name}' returned:\n{result}"
                            
                            # --- Fact Extractor Hook ---
                            if tool_name == "write_file":
                                filepath = args.get("filepath", "unknown")
                                if "agent_skills" in filepath:
                                    skill_name = filepath.split("agent_skills")[-1].replace("\\", "/").strip("/").split("/")[0]
                                    self.memory.store_fact(f"skill_{skill_name}", f"Registered new Python skill at {filepath}")
                                else:
                                    self.memory.store_fact(f"file_modified", f"Updated file {filepath}")
                            # ---------------------------

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
