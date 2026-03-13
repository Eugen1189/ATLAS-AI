import os
import re
import json
import inspect
from core.logger import logger
from core.security.guard import SecurityGuard

from core.system.discovery import EnvironmentDiscoverer
from core.brain.healer import Healer
from .base import BaseBrain

try:
    import ollama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

from core.brain.parser import parse_llm_response


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
        self.healer = Healer()
        if OLLAMA_AVAILABLE:
            self.client = ollama.Client(host=self.base_url)
        else:
            self.client = None

    def _load_dynamic_rules(self):
        try:
            if os.path.exists(self.dynamic_rules_path):
                with open(self.dynamic_rules_path, 'r', encoding='utf-8') as f:
                    self.dynamic_rules = json.load(f)
        except Exception:
            self.dynamic_rules = []

    def _add_dynamic_rule(self, rule: str):
        self.dynamic_rules.append(rule)
        os.makedirs(os.path.dirname(self.dynamic_rules_path), exist_ok=True)
        try:
            with open(self.dynamic_rules_path, 'w', encoding='utf-8') as f:
                json.dump(self.dynamic_rules, f, indent=4)
        except Exception:
            pass

    def _get_dynamic_context(self) -> str:
        """Dynamically identifies current system environment and project context."""
        cwd = os.path.abspath(os.getcwd())
        discovery_info = ""
        try:
            discoverer = EnvironmentDiscoverer()
            findings = discoverer.run_full_discovery(store_in_memory=False)
            
            ides = ", ".join(findings.get("ides", {}).keys()) or "None detected"
            tools = ", ".join(findings.get("tools", {}).keys()) or "Standard CLI"
            
            discovery_info = (
                f"### DETECTED ENVIRONMENT:\n"
                f"- **Working Directory**: `{cwd}`\n"
                f"- **Installed IDEs**: {ides}\n"
                f"- **Active Dev Tools**: {tools}\n"
                f"Note: This is a fresh, local environment. Never rely on past projects. "
                f"Always use `list_directory` to scan the filesystem before making assumptions.\n"
            )
        except Exception:
            discovery_info = f"### DETECTED ENVIRONMENT:\n- **Working Directory**: `{cwd}`\n"

        return discovery_info

    def _build_tool_manifest(self, tools: list) -> str:
        """
        Level 1 (Meta-Index): Builds a compact index of available tools.
        Only names and 1-sentence descriptions are shown.
        JSON Schemas are hidden until requested via 'get_tool_info'.
        """
        dynamic_context = self._get_dynamic_context()
        
        from datetime import datetime
        today = datetime.now().strftime("%B %d, %Y")
        
        manifest = (
            "## AXIS SYSTEM CORE (v3.0.0 - PRODUCTION)\n"
            "You are AXIS, the Command Intelligence for the Atlas Project. You act as a high-tier developer assistant and OS operator.\n"
            f"{dynamic_context}\n\n"
            "### CORE PROTOCOLS:\n"
            "1. **Communication**: Speak naturally and directly as the Commander's ally. Use the persona guidelines from memory if present.\n"
            "2. **Tool Execution**: If an action is required, output exactly ONE JSON object using `<tool_call>`. Do NOT repeat the JSON. Stop after the JSON.\n"
            "3. **Attention Management (Sharding)**: You only see short descriptions now. To see the full JSON schema of a tool (arguments, types), you MUST first use `get_tool_info(tool_name)`. Never guess arguments.\n"
            "4. **Visual Proof**: For critical system modifications, ALWAYS use `take_screenshot` + `send_telegram_photo` to provide visual evidence.\n"
            "5. **Proactivity**: You have full permission to manage paths, create logs/backups, and fix errors using `healer` suggestions.\n"
            f"6. **Environment**: Windows Host. Today's Date: {today}. Root: `{os.getcwd()}`.\n"
            "7. **Cross-Project Impact**: Before refactoring core modules, ALWAYS use `find_code_usages` to evaluate the impact on other modules.\n\n"
            "### CAPABILITIES INDEX (Level 1 Sharding):\n"
        )
        
        # [MCP Ecosystem Integration]
        from agent_skills.mcp_hub.bridge import get_bridge
        bridge = get_bridge()
        for server_name, session in bridge.sessions.items():
            if server_name == "internal": continue 
            manifest += f"\n[MCP: {server_name.upper()}]\n"
            manifest += f"- This server is connected via Model Context Protocol. Use its tools natively.\n"

        # Native Categorized view
        for category, tool_list in self.tool_index.items():
            manifest += f"\n[{category}]\n"
            for t_info in tool_list:
                manifest += f"- {t_info['name']}: {t_info['description']}\n"
                
        # Register tools in map for execution
        for tool in tools:
            name = getattr(tool, '__name__', str(tool))
            self.tool_map[name] = {"func": tool, "mcp": False}
            
        return manifest

    def get_tool_info(self, tool_name: str) -> str:
        """Level 2 (Hydration): Returns the full JSON schema for a specific tool."""
        if tool_name not in self.tool_map:
            return f"Error: Tool '{tool_name}' not found."
        
        tool_data = self.tool_map[tool_name]
        
        # If it's a native tool
        if not tool_data.get("mcp", False):
            tool = tool_data["func"]
            doc = getattr(tool, '__doc__', '') or 'No description.'
            try:
                sig = inspect.signature(tool)
                schema = {}
                for p_name, param in sig.parameters.items():
                    if p_name in ["kwargs", "args"]: continue
                    p_type = "any"
                    if param.annotation != inspect.Parameter.empty:
                        p_type = getattr(param.annotation, '__name__', str(param.annotation).replace('typing.', ''))
                    schema[p_name] = p_type
                
                return json.dumps({
                    "tool_name": tool_name,
                    "description": doc,
                    "arguments": schema,
                    "example": f"{{\"tool_name\": \"{tool_name}\", \"arguments\": {json.dumps({k: '...' for k in schema})}}}"
                }, indent=2, ensure_ascii=False)
            except Exception as e:
                return f"Error retrieving schema for {tool_name}: {e}"
        else:
            # If it's an MCP tool, we'd ideally fetch its schema via MCP
            return f"MCP Tool: {tool_name}. Use it with standard arguments as described in MCP docs."


    def initialize(self, available_tools: list, tool_index: dict = None):
        if not OLLAMA_AVAILABLE:
            logger.error("ollama.missing", reason="ollama python package is not installed")
            return False

        # Use shared initialization logic
        super().initialize(available_tools, tool_index=tool_index)

        self.available_tools = available_tools
        self.tool_map["get_tool_info"] = {"func": self.get_tool_info, "mcp": False} # Register hydration tool FIRST
        
        self.system_prompt = self._build_tool_manifest(available_tools)
        self.system_prompt += self.bp_manager.get_system_prompt_addon()
        self.system_prompt += self.memory.get_context_for_prompt()

        self._load_dynamic_rules()
        if self.dynamic_rules:
            self.system_prompt += "\n\n### ADAPTIVE MICRO-RULES (Learned from past errors):\n"
            for i, rule in enumerate(self.dynamic_rules, 1):
                self.system_prompt += f"{i}. {rule}\n"
        
        self.history = [{"role": "system", "content": self.system_prompt}]
        self.tool_map["switch_personality_blueprint"] = {"func": self.switch_personality_blueprint, "mcp": False}
        
        logger.info("ollama.initialized", 
                    model=self.model_name, 
                    tools_count=len(self.tool_map),
                    sharding="ACTIVE",
                    blueprint=self.bp_manager.active_blueprint.get("name"))
        return True

    def switch_personality_blueprint(self, name: str) -> str:
        result = self.bp_manager.switch_blueprint(name)
        self.system_prompt = self._build_tool_manifest(self.available_tools)
        self.system_prompt += self.bp_manager.get_system_prompt_addon()
        self.system_prompt += self.memory.get_context_for_prompt()
        self.history[0] = {"role": "system", "content": self.system_prompt}
        return result

    def check_model_health(self) -> bool:
        if not self.client:
            logger.error("ollama.health_check_failed", reason="Ollama client is not initialized.")
            return False
            
        try:
            models_response = self.client.list()
            downloaded_models = [m.get("model", "") for m in models_response.get("models", [])]
            model_exists = any(self.model_name in m for m in downloaded_models)
            
            if model_exists:
                logger.info("ollama.model_ready", model=self.model_name, status="OK")
                return True
            else:
                logger.warning("ollama.model_missing", model=self.model_name)
                return False
        except Exception as e:
            logger.error("ollama.server_offline", error=str(e))
            return False

    def _prune_history(self):
        """
        Summary Buffering: Every 20 turns, compresses history into a summary.
        Prevents logic degradation and context overflow.
        """
        if len(self.history) < 25: # Keep system + last 24 messages
            return
            
        logger.info("brain.summary_buffering", reason="Long history detected")
        
        # We take messages from index 1 (after system) up to index -10 (keep last 10)
        to_summarize = self.history[1:-10]
        
        try:
            summary_prompt = "Стисло підсумуй основні факти та результати з цієї переписки одним абзацом. Це буде використано як контекст для наступних повідомлень."
            messages = [{"role": "system", "content": "You are a summarization assistant."},
                        {"role": "user", "content": f"Context:\n{json.dumps(to_summarize)}\n\n{summary_prompt}"}]
            
            response = self.client.chat(model=self.model_name, messages=messages)
            summary = response['message']['content']
            
            # Reconstruct history: [System, Summary (as User or System), Last 10]
            new_history = [self.history[0]] # System prompt
            new_history.append({"role": "user", "content": f"### ПЕРЕДІСТОРІЯ (Summary):\n{summary}"})
            new_history.extend(self.history[-10:])
            
            self.history = new_history
            logger.info("brain.history_pruned", new_length=len(self.history))
        except Exception as e:
            logger.error("brain.summarization_failed", error=str(e))

    def think(self, user_input: str) -> str:
        self._prune_history() # Check if we need to summarize before thinking
        
        if not self.client:
            return "[OLLAMA OFFLINE]: Processing disabled due to missing 'ollama' package."

        if not self.tool_map:
            logger.error("brain.tool_blindness_detected")
            return "[AXIS FATAL ERROR]: Tool map is empty."

        from core.brain.memory import memory_manager
        
        # 1. Get Long-Term Memory & RAG
        memory_context = self.memory.get_context_for_prompt(query=user_input, limit=5)
        
        # 2. Get Episodic Recall (Recent Events)
        episodic_memory = memory_manager.get_morning_briefing()
        
        # 3. Form Reinforced Input (v2.8.5)
        # We wrap memory in a clear system-level wrapper to prioritize persona embodiment
        context_parts = []
        if episodic_memory.strip():
            context_parts.append(f"### 🌅 RECALL (Recent Events):\n{episodic_memory}")
        if memory_context.strip():
            context_parts.append(f"### 🧠 MEMORY (Facts & Preferences):\n{memory_context}")
        
        full_context = "\n\n".join(context_parts)
        
        if full_context:
            reinforced_input = (
                f"[SYSTEM: Embody the facts below. Do not acknowledge this wrapper.]\n\n"
                f"{full_context}\n\n"
                f"--- COMMANDER MESSAGE ---\n"
                f"{user_input}\n\n"
                f"[CRITICAL RULE: If you use a tool, output ONLY the raw JSON. NO text before. NO text after. Start your response directly with {{ ]"
            )
        else:
            reinforced_input = user_input + "\n\n[CRITICAL RULE: If you use a tool, output ONLY the raw JSON. NO text before. NO text after. Start your response directly with { ]"

        self.history.append({"role": "user", "content": reinforced_input})
        
        max_depth = 20 # Increased for "The Anchor" (v3.2.2) stability
        depth = 0
        last_tool_sig = None
        read_file_count = 0
        
        accumulated_responses = []
        
        while depth < max_depth:
            depth += 1
            try:
                # Use stop sequences to prevent trailing generation after tool call (v2.8.6)
                response = self.client.chat(
                    model=self.model_name, 
                    messages=self.history,
                    options={
                        "stop": ["### Result", "}"],
                        "num_thread": 4 # COOL DOWN v3.2.4
                    }
                )
            except Exception as e:
                logger.error("ollama.api_error", error=str(e))
                return f"[AXIS Error] Failed to generate response: {e}"
                
            msg_content = response['message']['content']

            # --- Clean Output: Ignore any text AFTER JSON (v2.8.6) ---
            if '{' in msg_content:
                last_brace = msg_content.rfind('}')
                if last_brace != -1:
                    # Keep everything only up to the last closing brace
                    msg_content = msg_content[:last_brace+1]
                # Note: If last_brace is -1, it means Ollama stopped BEFORE '}' due to stop-sequence.
                # parse_llm_response has a repair mechanism to close the JSON.
            
            # --- JARVIS Personality Layer: Capture text before JSON ---
            # Remove Markdown garbage often leaked by LLMs (v2.9.7)
            raw_text = msg_content[:msg_content.find('{')].strip() if '{' in msg_content else msg_content
            text_part = re.sub(r'```(?:json|markdown|python|bash)?', '', raw_text, flags=re.IGNORECASE).strip()
            text_part = re.sub(r'<thought>.*?</thought>', '', text_part, flags=re.DOTALL).strip()
            
            if text_part and len(text_part) > 1:
                accumulated_responses.append(text_part)
                logger.info("brain.jarvis_voice", text=text_part)

            # --- Repeat Loop Protection ---
            current_sig = hash(msg_content)
            if current_sig == last_tool_sig:
                 return "🛑 [AXIS LOOP BREAKER]: Repeated tool call detected."
            last_tool_sig = current_sig

            self.history.append({"role": "assistant", "content": msg_content})
            
            # --- Ironclad Parser Interaction ---
            tool_call = parse_llm_response(msg_content)
            
            if tool_call:
                try:
                    tool_name = tool_call.get("tool_name")
                    args = tool_call.get("arguments", {})

                    if tool_name not in self.tool_map:
                         raise NameError(f"Tool '{tool_name}' is not registered.")

                    # --- ARGUMENT VALIDATION (v3.0.0) ---
                    if not args and tool_name not in ["take_screenshot", "get_active_window", "hot_reload_skills", "get_workspace_summary"]:
                        raise ValueError(f"Tool '{tool_name}' called with empty arguments. You MUST provide valid parameters or use 'get_tool_info' to see the schema.")

                    # --- Security Check ---
                    target = str(args.get("filepath", args.get("path", args.get("command", ""))))
                    is_safe = SecurityGuard.is_safe_command(target) if "command" in args else SecurityGuard.is_safe_path(target, check_core=True)
                    
                    if not is_safe:
                        result = f"🚨 [SECURITY REJECTED]: Access forbidden."
                    else:
                        logger.info("ollama.executing_tool", tool=tool_name, args=args)
                        
                        tool_data = self.tool_map[tool_name]
                        if tool_data.get("mcp", False):
                            # MCP Execution
                            from agent_skills.mcp_hub.bridge import get_bridge
                            import asyncio
                            bridge = get_bridge()
                            
                            async def _call(): return await bridge.call_tool(tool_data["server"], tool_name, args)
                            
                            import nest_asyncio
                            nest_asyncio.apply()
                            loop = asyncio.get_event_loop()
                            result = loop.run_until_complete(_call())
                        else:
                            # Native Execution
                            result = tool_data["func"](**args)
                        
                    self.history.append({"role": "user", "content": f"### Result of {tool_name}:\n{result}"})

                    # --- Auto-Forwarding (v2.7.26.2) ---
                    if tool_name == "execute_command" and ("tree" in str(args.get("command", "")) or "core" in str(args)):
                        if "send_telegram_message" in self.tool_map:
                            # Send result as HTML-formatted text to Telegram
                            safe_result = str(result)[:3500].replace('<', '&lt;').replace('>', '&gt;')
                            formatted_result = f"🌳 <b>Звіт по дереву файлів:</b>\n<pre>{safe_result}</pre>"
                            tg_tool = self.tool_map["send_telegram_message"]["func"]
                            tg_res = tg_tool(text=formatted_result)
                            logger.info("brain.auto_forwarding", action="tree_report", destination="telegram", tg_result=tg_res)
                            
                            accumulated_responses.append("✅ [AXIS]: Звіт по дереву згенеровано та автоматично відправлено в Telegram.")
                            return "\n\n".join(accumulated_responses)
                    
                    # --- Loop Breaker for Telegram/Visual Confirmations ---
                    if tool_name in ["send_telegram_photo", "send_home_report"]:
                        logger.info("brain.jarvis_voice", text="Loop Breaker applied after visual confirmation.")
                        accumulated_responses.append(f"[AXIS LOOP BREAKER]: Action completed and confirmed via {tool_name}.")
                        return "\n\n".join(accumulated_responses)

                    # --- Pedal-To-The-Metal v2.7.26: Loop breaker with Force-Proof ---
                    if tool_name == "read_file":
                        read_file_count += 1
                        if read_file_count >= 2:
                            logger.warning("brain.pedagogical_loop", reason="Breaking cycle with visual proof")
                            
                            # Замість простої зупинки, ми ПРИМУСОВО робимо скріншот і відправляємо в TG
                            if "take_screenshot" in self.tool_map and "send_telegram_photo" in self.tool_map:
                                snap_path = self.tool_map["take_screenshot"]["func"]()
                                self.tool_map["send_telegram_photo"]["func"](
                                    filepath=snap_path, 
                                    caption="🚀 [AXIS AUTO-RECOVERY]: Task executed after pedagogical loop break."
                                )
                                msg = f"✅ [AXIS]: Цикл читання розірвано. Візуальний звіт надіслано в Telegram."
                            else:
                                msg = "🛑 [AXIS]: Stopped loop, but visual tools unavailable."
                                
                            accumulated_responses.append(msg)
                            return "\n\n".join(accumulated_responses)

                    continue

                except Exception as e:
                    error_msg = str(e)
                    
                    # Звертаємося до Healer
                    error_type = self.healer.diagnose(error_msg)
                    fix_suggestion = self.healer.propose_fix(error_type, tool_call)
                    
                    if error_type == "tool_not_found":
                        # Trigger incremental re-scan (V2.8.9 Logic)
                        try:
                            from core.system.discovery import EnvironmentDiscoverer
                            disc = EnvironmentDiscoverer()
                            # Check if it was a command in execute_command
                            target_tool = tool_call.get("arguments", {}).get("command", "").split(" ")[0] if tool_name == "execute_command" else tool_name
                            disc.incremental_scan(target_tool=target_tool)
                        except Exception: pass

                    logger.warning("brain.healer_active", type=error_type, suggestion=fix_suggestion)
                    
                    # --- HEALER 2.0: Autonomous Re-mapping (v3.2.7) ---
                    if error_type == "missing_argument" and "filepath" in str(args):
                        logger.info("brain.healer_2.0", action="auto_remapping", from_key="filepath", to_key="path")
                        # Swap filepath with path if it exists
                        new_args = args.copy()
                        new_args["path"] = new_args.pop("filepath")
                        try:
                            # Immediate re-execution attempt
                            tool_data = self.tool_map[tool_name]
                            if tool_data.get("mcp", False):
                                from agent_skills.mcp_hub.bridge import get_bridge
                                import asyncio
                                bridge = get_bridge()
                                async def _call(): return await bridge.call_tool(tool_data["server"], tool_name, new_args)
                                import nest_asyncio
                                nest_asyncio.apply()
                                loop = asyncio.get_event_loop()
                                result = loop.run_until_complete(_call())
                            else:
                                result = tool_data["func"](**new_args)
                            
                            self.history.append({"role": "user", "content": f"### Result of {tool_name} (Auto-Remapped):\n{result}"})
                            continue # Success!
                        except Exception as e2:
                            error_msg = f"{error_msg} (Remap failed: {e2})"

                    # Fallback to model correction
                    correction_context = f"🚨 ERROR: {error_msg}\n💡 HEALER SUGGESTION: {fix_suggestion}"
                    self.history.append({"role": "user", "content": correction_context})
                    
                    # Дозволяємо моделі ще одну спробу (depth вже інкрементований)
                    continue
            
            # If no tool call, we are done. (v2.9.7: Refined Return)
            final_spoken = "\n\n".join(accumulated_responses)
            if final_spoken.strip():
                return final_spoken
            
            # If nothing was spoken, return the message content or a standard confirmation
            return msg_content if msg_content.strip() else "✅ [AXIS]: Операцію завершено."
            
        return "[AXIS Error]: Exceeded maximum tool call depth."
