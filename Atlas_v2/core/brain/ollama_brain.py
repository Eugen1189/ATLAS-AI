import os
import re
import json
import inspect
from datetime import datetime
from core.logger import logger
from core.security.guard import SecurityGuard
from core.brain.healer import Healer
from core.brain.parser import parse_llm_response
from core.brain.memory import memory_manager

try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class OllamaBrain:
    """
    Ollama-based brain for local execution.
    Optimized for Qwen2.5-Coder:7b and similar models.
    """
    def __init__(self, model_name=None):
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = Client(host=self.base_url) if OLLAMA_AVAILABLE else None
        self.tool_map = {}
        self.history = []
        self.system_prompt = ""
        self.healer = Healer()
        
    def initialize(self, available_tools: list, tool_index: dict = None):
        if not OLLAMA_AVAILABLE:
            logger.error("ollama.missing")
            return False

        self.available_tools = available_tools
        self.tool_map = {tool.__name__: {"func": tool, "mcp": getattr(tool, 'mcp', False)} for tool in available_tools}
        
        # Build manifest with full schemas (De-sharded v3.3.0)
        self.system_prompt = self._build_tool_manifest(available_tools)
        
        # 2. Add core engineering protocols (v3.5.0)
        self.system_prompt += (
            "\n### CORE OPERATIONAL PROTOCOLS:\n"
            "1. IDENTITY: You are AXIS, a Task-Focused Engineering Assistant. Complete the specific task provided.\n"
            "2. FOCUS: Only perform actions directly related to the current task. DO NOT refactor code or run diagnostics unless explicitly asked.\n"
            "3. REPORTING: If you read a file or query a database, YOU MUST include the findings in your final response.\n"
            "4. PATHS: Always use full absolute paths with project subfolders (C:/Projects/LegalMind/...). NEVER guess paths.\n"
            "5. NO PLACEHOLDERS: Provide FULL content in tool calls. No '...' or '# placeholder'.\n"
            "6. COMPLETION: Once the specific goal is reached, present the result and end with 'MISSION ACCOMPLISHED'.\n"
            "7. SOURCE OF TRUTH: The disk is the only source of truth for file content. If you need to know what is in a file, use 'read_file'. DO NOT rely on memory/RAG for code details.\n"
            "8. EXECUTION BIAS: Prioritize tools that change or run state (write_file, execute_command, query_database) over diagnostics (search_memory, analyze_performance).\n"
            "9. SCHEMA-FIRST: DO NOT guess database structure. Always call 'get_db_schema' before querying a new table.\n"
            "10. NO TELEGRAM SPAM: Do not use 'send_telegram_message' for confirming technical steps or reporting every error. Solve technical issues autonomously via the Healer loop. Use Telegram ONLY for the final mission report or critical HITL blockers.\n"
            "11. LANGUAGE: Respond only in English or Ukrainian.\n"
        )
        
        self.history = [{"role": "system", "content": self.system_prompt}]
        logger.info("ollama.initialized", model=self.model_name, tools=len(self.tool_map))
        return True

    def _build_tool_manifest(self, tools):
        manifest = "### AVAILABLE TOOLS (JSON format required):\n"
        for tool in tools:
            name = tool.__name__
            try:
                sig = inspect.signature(tool)
                doc = (inspect.getdoc(tool) or "No description.").split('\n')[0]
                manifest += f"- {name}{sig}: {doc}\n"
            except:
                manifest += f"- {name}: (Complex signature)\n"
        return manifest

    def think(self, user_input: str) -> str:
        if not self.client: return "Ollama client not available."
        
        # [v3.4.5] Adaptive History Pruning: Keep system + last N messages
        if len(self.history) > 20: # Lowered to prevent 7b degradation
             self.history = [self.history[0]] + self.history[-10:]

        # Directive Reinforcement (v3.4.5)
        memory_context = memory_manager.get_morning_briefing()
        
        directive = (
            f"### SYSTEM STATE:\n{memory_context}\n\n"
            f"### CURRENT TASK:\n{user_input}\n\n"
            "### EXECUTION PROTOCOL (STRICT):\n"
            "1. If you need to use a tool, provide a valid JSON object: {\"tool_name\": \"...\", \"arguments\": {...}}\n"
            "2. Do NOT use placeholders like '...' or 'path/to/file'. Use REAL values from the task.\n"
            "3. If you have finished the task and verified it, end with 'MISSION ACCOMPLISHED'.\n"
            "4. IMPORTANT: Do NOT explain your thoughts. Just call the tool or give the final answer.\n"
            "5. ONLY use tools listed in your system prompt. DO NOT guess tool names or MCP servers.\n"
            "LANGUAGE: English or Ukrainian only."
        )

        self.history.append({"role": "user", "content": directive})
        
        max_depth = 12
        depth = 0
        accumulated_responses = []
        call_history = {} # [PROTOCOL 2.0] Tracking call counts for loop prevention
        any_success = False

        while depth < max_depth:
            depth += 1
            try:
                # [REPAIR v3.4.6] Forced context window to 8192 for stability
                response = self.client.chat(
                    model=self.model_name, 
                    messages=self.history,
                    options={"num_ctx": 8192, "temperature": 0.1}
                )
            except Exception as e:
                logger.error("ollama.api_error", error=str(e))
                return f"[OLLAMA ERROR]: {e}"

            msg_content = response['message']['content'].strip()
            if not msg_content:
                if depth == 1: continue 
                break
            
            tool_call = parse_llm_response(msg_content)
            text_part = msg_content
            json_match = re.search(r'\{.*\}', msg_content, flags=re.DOTALL)
            if json_match:
                text_part = msg_content.replace(json_match.group(0), "")
            
            text_part = re.sub(r'```(?:json)?', '', text_part).replace('```', '').strip()
            if text_part and len(text_part) > 3:
                accumulated_responses.append(text_part)

            if tool_call:
                tool_name = tool_call.get("tool_name")
                args = tool_call.get("arguments", {})
                
                if tool_name not in self.tool_map:
                    self.history.append({"role": "assistant", "content": msg_content})
                    self.history.append({"role": "user", "content": f"### ERROR: Tool '{tool_name}' not found."})
                    continue

                if isinstance(args, dict):
                    for wrong in ["filepath", "file_path", "filePath", "item_path", "target", "item"]:
                        if wrong in args and "path" not in args:
                            args["path"] = args[wrong]
                    if "path" in args and isinstance(args["path"], str):
                        args["path"] = args["path"].replace('`', '').strip()

                call_sig = f"{tool_name}:{json.dumps(args, sort_keys=True)}"
                
                # [PROTOCOL 2.0] Infinite Loop Prevention (Retry Limit = 2)
                # We allow up to 2 identical calls if they are retries for self-healing
                call_count = call_history.get(call_sig, 0)
                from core.system.router import SemanticRouter
                limit = getattr(SemanticRouter, "RETRY_LIMIT", 2)

                if call_count >= limit and tool_name not in ["take_screenshot", "list_directory", "read_file"]:
                     self.history.append({"role": "assistant", "content": msg_content})
                     self.history.append({"role": "user", "content": f"### SYSTEM: Action '{tool_name}' failed with these arguments {limit} times. STOP. Request human assistance or try a completely different approach."})
                     continue
                
                call_history[call_sig] = call_count + 1

                try:
                    logger.info("ollama.executing", tool=tool_name, args=args)
                    check_path = args.get("path")
                    if check_path and not SecurityGuard.is_safe_path(check_path):
                        result = "🚨 [SECURITY]: Access denied."
                    else:
                        tool_data = self.tool_map[tool_name]
                        result = tool_data["func"](**args)
                    
                    self.history.append({"role": "assistant", "content": msg_content})

                    # [PROTOCOL 2.0] Integrity Check: Do not set success if command failed or was blocked
                    if "🚨" in result or "❌" in result:
                        diagnosis = self.healer.diagnose(result)
                        # Add partial result for context if unknown
                        last_action_context = tool_call.copy()
                        last_action_context["result"] = result
                        fix_prompt = self.healer.propose_fix(diagnosis, last_action_context)
                        self.history.append({"role": "user", "content": f"### Result of {tool_name}:\n{result}\n\n{fix_prompt}"})
                        continue

                    any_success = True
                    self.history.append({"role": "user", "content": f"### Result of {tool_name}:\n{result}"})
                    continue 
                except Exception as e:
                    self.history.append({"role": "assistant", "content": msg_content})
                    # [PROTOCOL 2.0] Healer integration for general exceptions
                    diagnosis = self.healer.diagnose(str(e))
                    fix_prompt = self.healer.propose_fix(diagnosis, tool_call)
                    self.history.append({"role": "user", "content": f"### Execution Error: {e}.\n\n{fix_prompt}"})
                    continue
            else:
                # If no tool call and not finished, re-prompt once (v3.4.2)
                if not any_success and "MISSION ACCOMPLISHED" not in msg_content and depth < 3:
                    self.history.append({"role": "assistant", "content": msg_content})
                    self.history.append({"role": "user", "content": "### SYSTEM: No tool call detected. You MUST provide a JSON tool call to proceed."})
                    continue
                
                self.history.append({"role": "assistant", "content": msg_content})
                break

        if accumulated_responses:
            final_response = "\n\n".join(accumulated_responses)
        else:
            final_response = msg_content

        # [REPAIR v3.4.7] Auto-Reporting: Ensure user sees significant tool outputs
        if any_success and ("MISSION ACCOMPLISHED" in final_response or len(final_response) < 50):
            # Find the last meaningful result in history
            results = [m['content'] for m in self.history if m['role'] == 'user' and '### Result of' in m['content']]
            if results:
                last_result = results[-1].replace("### Result of ", "Execution Output (")
                final_response = f"{final_response}\n\n{last_result}"
        
        return final_response
