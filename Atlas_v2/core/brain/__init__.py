import os
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
            
        import google.generativeai as genai
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
        self.dynamic_rules_path = "memories/dynamic_rules.json"
        self.dynamic_rules = []
        if OLLAMA_AVAILABLE:
            self.client = ollama.Client(host=self.base_url)
        else:
            self.client = None

    def _load_dynamic_rules(self):
        try:
            if os.path.exists(self.dynamic_rules_path):
                import json
                with open(self.dynamic_rules_path, 'r', encoding='utf-8') as f:
                    self.dynamic_rules = json.load(f)
        except Exception:
            self.dynamic_rules = []

    def _add_dynamic_rule(self, rule: str):
        self.dynamic_rules.append(rule)
        os.makedirs(os.path.dirname(self.dynamic_rules_path), exist_ok=True)
        try:
            import json
            with open(self.dynamic_rules_path, 'w', encoding='utf-8') as f:
                json.dump(self.dynamic_rules, f, indent=4)
        except Exception:
            pass

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
            "### CORE ENVIRONMENT & OPERATIONAL RULES:\n"
            "1. **Platform & Skills**: Python 3.12 (AXIS V2.5). Skills require `__init__.py` and `manifest.py` in `agent_skills/`.\n"
            "2. **No-Chat Mode**: Do not engage in social chatter. Be concise.\n"
            "3. **Streaming Thought**: ALWAYS wrap your reasoning in <thought>...</thought> tags before calling any tools.\n"
            "4. **Negative Constraints**: NEVER run non-existent files. ALWAYS verify state (list_dir) before acting.\n"
            "5. **Tool Integrity**: Use ONLY predefined arguments. 'Validation' and 'Authorization' DO NOT exist.\n"
            "6. **JSON Purity**: Output ONLY raw JSON object. No markdown backticks unless strictly required by tool.\n"
            "7. **Error Correction**: Analyze errors before retrying. Do not repeat broken commands.\n"
            "8. **Task Completion**: End strictly with 'Task Complete'. No unsolicited sub-tasks.\n"
            "9. **System Modding**: DO NOT create Bash/Shell scripts. Always use `structlog`.\n\n"
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

        # Load Dynamic Rules and attach them
        self._load_dynamic_rules()
        if self.dynamic_rules:
            self.system_prompt += "\n\n### ADAPTIVE MICRO-RULES (Learned from past errors):\n"
            for i, rule in enumerate(self.dynamic_rules, 1):
                self.system_prompt += f"{i}. {rule}\n"
        
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
            
            # Extract and log Streaming Thought
            import re
            thought_match = re.search(r'<thought>(.*?)</thought>', msg_content, re.DOTALL)
            if thought_match:
                logger.info("ollama.streaming_thought", thought=thought_match.group(1).strip())
                
            self.history.append({"role": "assistant", "content": msg_content})
            
            # Check if there is a JSON tool request
            json_str = ""
            if "```json" in msg_content and "```" in msg_content.split("```json", 1)[1]:
                json_str = msg_content.split("```json")[1].split("```")[0].strip()
            elif "{" in msg_content and "}" in msg_content:
                json_str = msg_content[msg_content.find("{"):msg_content.rfind("}")+1]
                
            if json_str:
                try:
                    # Handle triple quotes
                    if '"""' in json_str:
                        json_str = json_str.replace('"""', '"')
                        
                    decoder = json.JSONDecoder(strict=False)
                    pos = 0
                    parsed_objects = []
                    while pos < len(json_str):
                        while pos < len(json_str) and json_str[pos].isspace():
                            pos += 1
                        if pos >= len(json_str):
                            break
                        try:
                            obj, idx = decoder.raw_decode(json_str[pos:])
                            if isinstance(obj, dict):
                                parsed_objects.append(obj)
                            pos += idx
                        except json.JSONDecodeError:
                            next_brace = json_str.find('{', pos + 1)
                            if next_brace != -1:
                                pos = next_brace
                            else:
                                break
                    
                    if not parsed_objects:
                        raise ValueError("No valid JSON objects found")
                        
                    tool_result_str = ""
                    for req in parsed_objects:
                        tool_name = req.get("tool_name")
                        args = req.get("arguments", {})
                        
                        if tool_name in self.tool_map:
                            from core.security.guard import SecurityGuard
                            
                            # Fast guard check based on standard path/command argument naming
                            file_context = args.get("filepath", args.get("path", args.get("command", "")))
                            is_safe = SecurityGuard.is_safe_command(file_context) if "command" in args else SecurityGuard.is_safe_path(file_context, check_core=True)
                            
                            if not is_safe:
                                tool_result_str += f"[SECURITY BLOCK] Action rejected by System Guard. Target path or command violates security context.\n"
                                logger.warning("ollama.security_guard_blocked", tool=tool_name, context=file_context)
                                continue

                            # --- Double-Pass Reasoning (Internal Review & Sandboxed Validation) ---
                            review_prompt = (
                                f"Pre-flight Check / Internal Review: You proposed executing '{tool_name}' with args {args}. "
                                "1. Does this action safely respect the architecture? "
                                "2. If updating or deleting a file, ensure it does not permanently damage core systems. "
                                "Accessing project-related paths like 'C:/Projects/Atlas' or local subdirectories is ALWAYS APPROVED. "
                                "Only reject actions involving system-critical paths like 'C:/Windows', 'core/' override without care, or 'rm -rf'. "
                                "Evaluate your confidence in the safety and correctness of this action. "
                                "Reply ONLY in this exact format: 'CONFIDENCE: <0-100>% | STATUS: <APPROVED/REJECTED> | REASON: <Explanation>'"
                            )
                            try:
                                review_response = self.client.chat(model=self.model_name, messages=[{"role": "user", "content": review_prompt}])
                                review_res_content = review_response['message']['content'].strip()
                                
                                conf_match = re.search(r'CONFIDENCE:\s*(\d+)%', review_res_content.upper())
                                status_match = re.search(r'STATUS:\s*(APPROVED|REJECTED)', review_res_content.upper())
                                
                                confidence = int(conf_match.group(1)) if conf_match else 100
                                status = status_match.group(1) if status_match else "APPROVED"
                                
                                logger.info("ollama.internal_review", confidence=confidence, status=status)
                                
                                if status != "APPROVED":
                                    logger.warning("ollama.self_correction_rejected", tool=tool_name, reason=review_res_content)
                                    tool_result_str += f"Internal Review REJECTED the tool '{tool_name}': {review_res_content}\n"
                                    continue
                                    
                                if confidence < 70:
                                    logger.warning("ollama.low_confidence_blocked", tool=tool_name, confidence=confidence)
                                    tool_result_str += f"[SYSTEM BLOCK]: Action '{tool_name}' blocked due to low confidence ({confidence}%). I am not 100% sure this action is safe. Please manually confirm or clarify your request.\n"
                                    continue
                                    
                            except Exception as e:
                                logger.warning("ollama.internal_review_error", error=str(e))
                            # -----------------------------------------------

                            logger.info("ollama.executing_tool", tool=tool_name, args=args)
                            tool_func = self.tool_map[tool_name]
                            
                            try:
                                # Execute the standard python tool
                                result = tool_func(**args)
                                tool_result_str += f"Tool '{tool_name}' returned:\n{result}\n"
                                
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
                                tool_result_str += f"Tool '{tool_name}' failed with error: {e}\n{traceback.format_exc()}\n"
                        else:
                            tool_result_str += f"Error: Tool '{tool_name}' is not recognized.\n"

                    # Feed the result back to Ollama
                    logger.debug("ollama.tool_result", result=str(tool_result_str)[:200])
                    self.history.append({"role": "user", "content": tool_result_str})
                    
                    # Loop back to let Ollama process the tool result
                    continue
                    
                except Exception as e:
                    logger.warning("ollama.invalid_json", json=json_str)
                    self.history.append({"role": "user", "content": f"Error: Invalid JSON format. Please try again. ({e})"})
                    continue
            
            # If no tool called, return the response text
            return msg_content
            
        # --- Post-Mortem Analysis (Healer Brain) ---
        try:
            healer_prompt = (
                "You are the AXIS Healer Brain. The main agent just got stuck in an infinite loop while trying to solve the user's task. "
                "Analyze its previous actions and errors. Why did it get stuck? Did it invent arguments? Did it ignore errors? "
                "Formulate ONE concise, strict 'Micro-Rule' (max 2 sentences) that starts with 'NEVER' or 'ALWAYS' to prevent this specific failure in the future. "
                "Output ONLY the rule."
            )
            # Create a localized temporary history to extract the rule
            healer_history = self.history[-15:] + [{"role": "user", "content": healer_prompt}]
            healer_response = self.client.chat(model=self.model_name, messages=healer_history)
            new_rule = healer_response['message']['content'].strip()
            self._add_dynamic_rule(new_rule)
            logger.warning("ollama.post_mortem_healed", new_rule=new_rule)
            return f"[AXIS Healing Protocol Activated]: I got stuck in a loop. I have self-diagnosed the issue and added a new Rule:\n\n'{new_rule}'\n\nPlease retry your request."
        except Exception as e:
            logger.error("ollama.healer_failed", error=str(e))
            return "[AXIS Error]: Exceeded maximum tool call depth. Healing protocol failed."

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
