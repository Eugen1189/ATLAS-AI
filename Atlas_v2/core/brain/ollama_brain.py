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
from core.brain.base import BaseBrain

try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False

class OllamaBrain(BaseBrain):
    """
    Ollama-based brain for local execution.
    Optimized for Qwen2.5-Coder:7b and similar models.
    """
    def __init__(self, model_name=None):
        super().__init__()
        self.model_name = model_name or os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")
        self.base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.client = Client(host=self.base_url) if OLLAMA_AVAILABLE else None
        self.tool_map = {}
        self.history = []
        self.system_prompt = ""
        self.healer = Healer()
        
    def reset_history(self):
        self.history = [{"role": "system", "content": self.system_prompt}]
        logger.debug("ollama.history_reset")

    def initialize(self, available_tools: list, tool_index: dict = None, workspace_root: str = None):
        if not OLLAMA_AVAILABLE:
            logger.error("ollama.missing")
            return False

        super().initialize(available_tools, tool_index=tool_index, workspace_root=workspace_root)

        self.available_tools = available_tools
        self.tool_map = {tool.__name__: {"func": tool, "mcp": getattr(tool, 'mcp', False)} for tool in available_tools}
        
        # Build manifest with full schemas (De-sharded v3.3.0)
        self.system_prompt = self._build_tool_manifest(available_tools)
        
        # 2. Add core engineering protocols (v3.5.0)
        self.system_prompt += (
            f"\n### REALITY ANCHOR:\n- CURRENT_WORKSPACE: {self.workspace_root}\n- FLUID_TRUST: You can READ information from any project in C:/Projects. You are strictly LOCKED to writing only in {self.workspace_root}.\n"
            "\n### CORE OPERATIONAL PROTOCOLS:\n"
            "1. IDENTITY: You are AXIS, a Task-Focused Engineering Assistant. Complete the specific task provided.\n"
            "2. FOCUS: Only perform actions directly related to the current task. Do exactly what is requested.\n"
            "3. REPORTING: If you read a file or query a database, YOU MUST include the findings in your final response.\n"
            f"4. PATHS: Always use ABSOLUTE paths (e.g., {self.workspace_root}/src/...). NEVER guess or invent paths.\n"
            "5. NO PLACEHOLDERS: Provide FULL content in tool calls. No '...' or '# placeholder'. Any use of '// code will be updated' is a CRITICAL FAILURE and will be rejected.\n"
            "6. COMPLETION: Once the specific goal is reached, present the result. For the final step of a task, include 'MISSION ACCOMPLISHED' at the end.\n"
            "7. SOURCE OF TRUTH: The disk is the only source of truth for file content. If you need to know what is in a file, use 'read_file'. DO NOT rely on memory/RAG for code details.\n"
            "8. MINIMALISM: Do exactly one action per step. Focus only on the requested task.\n"
            "9. EXECUTION BIAS: Prioritize tools that change state (write_file, apply_ast_patch). Avoid heavy audit tools (find_dead_code, find_code_duplicates) during simple navigation.\n"
            "10. INTEGRITY CHECK: You are forbidden from claiming mission success if any technical tool call failed. If a tool fails, you MUST fix it immediately via the Healer logic.\n"
            "11. NO REDUNDANT STUDY: Avoid calling 'get_tool_info' for tools you already see in your manifest. Prioritize ACTION over documentation unless absolutely necessary.\n"
            "12. NO PLACEHOLDERS: Use of square brackets like '[Insert ...]', '[Future Work]', or filling files with placeholders is a CRITICAL FAILURE. If you lack data, use 'google_research' to find it or state clearly that data is missing in your final report.\n"
            "13. SEARCH RESILIENCE: If a search tool returns 'no_results', you are forbidden from moving to the next step. You MUST refine your query (e.g., remove specific combined filters) and retry until you fetch real data.\n"
            "14. NO TELEGRAM SPAM: Do not use 'send_telegram_message' for technical steps or status updates. Use it ONLY for the final report to the Commander.\n"
            "15. LANGUAGE: Respond only in English or Ukrainian.\n"
            "16. SYNC-OR-FAIL: After creating tools, YOU MUST call 'hot_reload_skills'.\n"
            "17. IMPACT ANALYSIS: Before changing core files, use 'analyze_impact'.\n"
            "18. ANTI-VINAIGRETTE: Do NOT use 'append_to_file' for fixing bugs or adding functions to scripts. This creates 'Vinaigrette Error' (duplicate code/imports). Use 'write_file' for a clean rewrite or 'apply_ast_patch'.\n"
            "19. BUG RECOVERY: If a script fails (NameError, SyntaxError), YOUR FIRST ACTION MUST BE to 'read_file' to check the disk's truth, then 'write_file' a COMPLETE working version. NEVER guess the file's content based on previous steps.\n"
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
                doc = (inspect.getdoc(tool) or "").split('\n')[:5] # Keep first 5 lines
                doc_str = "\n  ".join([d.strip() for d in doc if d.strip()])
                manifest += f"- {name}{sig}:\n  {doc_str}\n"
            except:
                manifest += f"- {name}: (Complex signature)\n"
        return manifest

    def think(self, user_input: str) -> str:
        if not self.client: return "Ollama client not available."
        
        # [v3.4.5] Adaptive History Pruning: Keep system + last N messages
        # [UPGRADE v3.7.5] Smarter History Pruning: Keep system + last 18 messages
        if len(self.history) > 30: # Increased threshold for multi-step stability
             self.history = [self.history[0]] + self.history[-18:]

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
        last_tool_result = None

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
                    available = ", ".join(list(self.tool_map.keys())[:20])
                    self.history.append({"role": "assistant", "content": msg_content})
                    self.history.append({"role": "user", "content": (
                        f"### ERROR: Tool '{tool_name}' does NOT exist in your toolkit.\n"
                        f"### AVAILABLE TOOLS (pick from these only):\n{available}\n"
                        f"### ACTION: Use 'get_tool_info' to inspect any tool, or pick the closest match from the list above."
                    )})
                    continue

                if isinstance(args, dict):
                    # [HEALER v3.5.1] Catch empty arguments for required parameters
                    NO_ARG_TOOLS = [
                        "get_workspace_summary", "get_memory_stats", "list_mcp_capabilities", 
                        "deep_system_scan", "analyze_performance", "repair_environment",
                        "refresh_environment_discovery", "hot_reload_skills", "get_db_schema",
                        "refresh_code_index", "verify_code", "audit_dependencies", "analyze_architecture"
                    ]
                    if not args and tool_name not in NO_ARG_TOOLS:
                        self.history.append({"role": "assistant", "content": msg_content})
                        self.history.append({"role": "user", "content": f"### ERROR: You called '{tool_name}' with NO arguments. This tool requires specific parameters. Use 'get_tool_info' to see the required schema before retrying."})
                        continue

                    for wrong in ["filepath", "file_path", "filePath", "item_path", "target", "item"]:
                        if wrong in args and "path" not in args:
                            args["path"] = args[wrong]
                            
                    if "path" in args and isinstance(args["path"], str):
                        p = args["path"].replace('`', '').strip()
                        # [PATH HEALER v3.5.3] Strip invalid leading slash for Windows paths
                        if p.startswith("/") and len(p) > 2 and p[2] == ":":
                            p = p[1:]
                        
                        ws_root = self.workspace_root.replace("\\", "/").lower()
                        
                        # [PATH RECOVERY] If path starts with Atlas_v2 but misses Atlas/, fix it
                        if p.lower().startswith("atlas_v2") and not ws_root.endswith("atlas_v2"):
                            p = f"{ws_root}/Atlas_v2" + p[8:] if p[8:] else f"{ws_root}/Atlas_v2"
                        
                        p_abs = os.path.abspath(p).replace("\\", "/").lower()
                        
                        # Fix c:/projects/atlas_v2 -> c:/projects/atlas/atlas_v2
                        if "c:/projects/atlas_v2" in p_abs and ws_root == "c:/projects/atlas":
                            p_abs = p_abs.replace("c:/projects/atlas_v2", "c:/projects/atlas/atlas_v2")
                            p = p_abs
                        
                        # [v3.7.0] READ-ONLY and WORKSPACE tools may access sibling projects (fluid trust)
                        # Only WRITE/DELETE tools are hard-locked to workspace_root
                        READ_ONLY_TOOLS = {
                            "list_directory", "read_file", "search_files", "find_code_usages",
                            "switch_workspace", "open_workspace", "setup_new_project", "get_workspace_summary"
                        }
                        is_read_only = tool_name in READ_ONLY_TOOLS
                        
                        if not p_abs.startswith(ws_root) and "projects" in p_abs and not is_read_only:
                            self.history.append({"role": "assistant", "content": msg_content})
                            self.history.append({"role": "user", "content": (
                                f"### SECURITY: Write/Modify access to '{p}' is blocked (outside workspace: {ws_root}).\n"
                                "Project Lock Policy: You may READ any file in C:/Projects, but you can only WRITE to your current workspace. "
                                "To modify another project, ask the user to 'switch_workspace' or 'open_workspace'."
                            )})
                            continue

                        args["path"] = p

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
                        # [v3.7.0] Workspace tools are allowed to target outside paths as they update the root
                        if tool_name not in ["switch_workspace", "open_workspace", "setup_new_project"]:
                            result = "🚨 [SECURITY]: Access denied (Outside trusted workspace)."
                        else:
                            tool_data = self.tool_map[tool_name]
                            result = tool_data["func"](**args)
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
                    # [v3.7.6 OPTIMIZATION] Truncate long results to keep context window healthy
                    display_result = result
                    if isinstance(result, str) and len(result) > 2500:
                         display_result = result[:1200] + "\n... [TRUNCATED FOR STABILITY] ...\n" + result[-1200:]
                    
                    last_tool_result = result
                    self.history.append({"role": "user", "content": f"### Result of {tool_name}:\n{display_result}"})
                    # [v3.5.5] Clear accumulated thoughts if we have a successful tool call to reduce noise
                    if depth < 3: accumulated_responses = []
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
        if any_success and ("MISSION ACCOMPLISHED" in final_response or len(final_response) < 100):
            # If the response is too short or just a success message, append the last meaningful result
            if last_tool_result and last_tool_result not in final_response:
                final_response = f"{final_response}\n\n[LAST TOOL OUTPUT]:\n{last_tool_result}"
        
        # [v3.5.6] Anti-Hallucination: If model claims success but never ran a tool
        if "MISSION ACCOMPLISHED" in final_response and not any_success and depth > 1:
             final_response = f"[WARNING]: Agent claimed success without successful tool execution.\n\n{final_response}"
        
        return final_response
