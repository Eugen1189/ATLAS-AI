import os
import importlib
import sys
import asyncio
from pathlib import Path
from core.logger import logger
from core.system.path_utils import load_environment, get_project_root
load_environment()


from core.brain import BrainFactory  # noqa: E402
from core.brain.memory import memory_manager # noqa: E402
from core.system.path_utils import get_namespace_for_path # noqa: E402
class AxisCore:
    """Main logic for the AXIS agent orchestrator."""
    def __init__(self):
        logger.info("system.booting", version="3.2.8")
        
        self.project_root = str(get_project_root())
        os.chdir(self.project_root) # Force CWD to project root for all relative paths
        
        # 1. First Pass: Discovery (Zero-Config)
        primary_workspace = None
        try:
            from core.system.discovery import EnvironmentDiscoverer
            from core.security.guard import SecurityGuard
            
            # Initialize discovery with explicitly mapped root
            discoverer = EnvironmentDiscoverer(project_root=self.project_root)
            findings = discoverer.run_full_discovery(store_in_memory=False)
            primary_workspace = findings.get("primary_workspace") or self.project_root
            
            # Security: Apply Scoped Trust
            SecurityGuard.set_workspace(primary_workspace)
        except Exception as e:
            logger.warning("system.discovery_failed", error=str(e))

        # 2. Memory Context: Set Unique Namespace (v3.6.0)
        # Use a hash of the absolute path to prevent project collisions in RAG
        namespace = get_namespace_for_path(primary_workspace or self.project_root)
        
        # Update global memory_manager namespace before brain init
        memory_manager.switch_namespace(namespace)

        # 3. Load skills with categorization
        self.available_tools, self.tool_index = self._load_skills()
        
        # 3.5. Initialize MCP Protocol (Universal Bridge)
        import asyncio
        from agent_skills.mcp_hub.bridge import get_bridge
        self.mcp_bridge = get_bridge()
        
        # Setup MCP Connections in background or blocking
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.mcp_bridge.connect_internal())
                asyncio.create_task(self.mcp_bridge.connect_from_config())
            else:
                loop.run_until_complete(self.mcp_bridge.connect_internal())
                loop.run_until_complete(self.mcp_bridge.connect_from_config())
        except Exception as e:
            logger.warning("mcp.init_warning", error=str(e))

        # 4. Initialize the Executor (Local Model by default: Qwen 2.5 Coder)
        # Force executor to use Local Brain (Ollama) if possible for "silent" execution
        old_brain_env = os.getenv("AI_BRAIN", "ollama")
        os.environ["AI_BRAIN"] = os.getenv("EXECUTOR_BRAIN", "ollama")
        self.executor = BrainFactory.create_brain()
        
        # 5. Initialize the Planner (High-Reasoning model: Gemini)
        from core.brain.planner import Planner
        self.planner = Planner()
        
        try:
            # Initialize Executor
            exec_success = self.executor.initialize(self.available_tools, tool_index=self.tool_index, workspace_root=self.project_root)
            # Initialize Planner
            plan_success = self.planner.initialize(self.available_tools, self.tool_index, workspace_root=self.project_root)
            
            if not exec_success or not plan_success:
                logger.error("system.brain_init_failed", reason="Check API Keys for Gemini or Ollama status")
                # We can still proceed if at least one is working, or raise
                if not exec_success:
                    raise ValueError("Executor failed to initialize.")
        except Exception as e:
            logger.critical("system.core_fatal_error", error=str(e))
            raise
        finally:
            os.environ["AI_BRAIN"] = old_brain_env # Restore for other potential users
            # Keep a reference as 'brain' for backward compatibility with router/hot_reload
            self.brain = self.executor 

        # 5. Initialize Semantic Router
        from core.system.router import SemanticRouter
        self.router = SemanticRouter(self)

        # 6. Register system tools
        self.brain.tool_map["hot_reload_skills"] = {"func": self.hot_reload_skills, "mcp": False}
        self.brain.tool_map["get_tool_info"] = {"func": self.get_tool_info, "mcp": False}
        self.brain.tool_map["switch_workspace"] = {"func": self.switch_workspace, "mcp": False}

        logger.info("system.core_init_success", 
                    count=len(self.available_tools), 
                    categories=list(self.tool_index.keys()), 
                    namespace=namespace)
    
    def hot_reload_skills(self) -> str:
        """Reloads all skills from agent_skills folder without restarting AXIS."""
        logger.info("system.hot_reload_triggered")
        self.available_tools, self.tool_index = self._load_skills()
        
        # 1. Update Executor (Local Brain)
        exec_success = self.executor.initialize(self.available_tools, tool_index=self.tool_index, workspace_root=self.project_root)
        
        # 2. Update Planner (High-Reasoning Brain)
        plan_success = self.planner.initialize(self.available_tools, self.tool_index, workspace_root=self.project_root)
        
        if exec_success and plan_success:
            # Re-register tools that might have been lost
            self.executor.tool_map["hot_reload_skills"] = {"func": self.hot_reload_skills, "mcp": False}
            self.executor.tool_map["get_tool_info"] = {"func": self.get_tool_info, "mcp": False}
            self.executor.tool_map["switch_workspace"] = {"func": self.switch_workspace, "mcp": False}
            return f"[HOT RELOAD SUCCESS]: Loaded {len(self.available_tools)} tools across {len(self.tool_index)} categories. Planner synced."
        return "[HOT RELOAD FAILED]: Brain or Planner initialization error."

    def get_tool_info(self, tool_name: str) -> str:
        """Returns the full documentation and signature for a specific tool."""
        if tool_name not in self.brain.tool_map:
            return f"Error: Tool '{tool_name}' not found. Use 'get_workspace_summary' to see available categories."
        
        tool_data = self.brain.tool_map[tool_name]
        if tool_data.get("mcp"):
             return f"MCP Tool: {tool_name} on server {tool_data.get('server')}. Use 'list_mcp_capabilities' for details."
        
        func = tool_data["func"]
        import inspect
        try:
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or "No documentation available."
            return f"### Tool: {tool_name}\nSignature: {tool_name}{sig}\n\nDocumentation:\n{doc}"
        except Exception as e:
            return f"Error retrieving info for '{tool_name}': {e}"

    def switch_workspace(self, path: str) -> str:
        """
        [PROTOCOL 3.6] Shifts AXIS entire consciousness to a new project directory.
        Re-initializes Discovery, Memory (RAG), and Tools for the target path.
        """
        logger.info("system.switching_workspace", target=path)
        from core.system.path_utils import resolve_path, get_namespace_for_path
        
        abs_path = resolve_path(path)
        if not os.path.exists(abs_path) or not os.path.isdir(abs_path):
            return f"❌ [ERROR]: Path '{path}' is not a valid directory."
            
        self.project_root = abs_path
        os.chdir(self.project_root)
        
        # 1. Update Memory Namespace
        new_namespace = get_namespace_for_path(self.project_root)
        memory_manager.switch_namespace(new_namespace)
        
        # 2. Re-discover environment markers
        from core.system.discovery import EnvironmentDiscoverer
        from core.security.guard import SecurityGuard
        discoverer = EnvironmentDiscoverer(project_root=self.project_root)
        findings = discoverer.run_full_discovery(store_in_memory=False)
        primary = findings.get("primary_workspace") or self.project_root
        SecurityGuard.set_workspace(primary)
        
        # 3. Reload tools and re-init brains
        self.available_tools, self.tool_index = self._load_skills()
        
        exec_success = self.executor.initialize(self.available_tools, tool_index=self.tool_index, workspace_root=self.project_root)
        plan_success = self.planner.initialize(self.available_tools, self.tool_index, workspace_root=self.project_root)
        
        # Re-register system tools on the new brain instance tool_map
        self.brain = self.executor
        self.brain.tool_map["hot_reload_skills"] = {"func": self.hot_reload_skills, "mcp": False}
        self.brain.tool_map["get_tool_info"] = {"func": self.get_tool_info, "mcp": False}
        self.brain.tool_map["switch_workspace"] = {"func": self.switch_workspace, "mcp": False}
        
        if exec_success and plan_success:
            return f"✅ [WORKSPACE SWITCHED]: Consciousness shifted to '{os.path.basename(self.project_root)}'. RAG Namespace: {new_namespace}."
        return "⚠️ [PARTIAL SUCCESS]: Workspace switched, but some brains failed to initialize."

    def _load_skills(self):
        """Scans the agent_skills folder and loads EXPORTED_TOOLS with categorization."""
        tools = []
        tool_index = {} # Categorized meta-info
        
        skills_dir = Path(__file__).parent.parent / "agent_skills"
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        # Default Categories for Smart Sharding
        # Clean Core: Selected high-autonomy skills (v3.6.6)
        SKILL_CATEGORIES = {
            "file_master": "Files",
            "terminal_operator": "System",
            "diagnostics": "System",
            "memory_manager": "Memory",
            "web_research": "Web",
            "mcp_hub": "System",
            "telegram_bridge": "System",
            "code_intelligence": "Memory",
            "database_master": "Files",
            "architect": "System",
            "patch_protocol": "Memory",
            "code_auditor": "Audit", # Sharded away from System to prevent misuse
            "qa_sandbox": "Audit",
            "workspace_manager": "System"
        }

        if not skills_dir.exists():
            logger.warning("system.skills_dir_missing", path=str(skills_dir))
            return tools, tool_index

        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir() and (skill_folder / "manifest.py").exists():
                try:
                    module_path = f"agent_skills.{skill_folder.name}.manifest"
                    if module_path in sys.modules:
                        importlib.reload(sys.modules[module_path])
                    
                    module = importlib.import_module(module_path)
                    
                    if hasattr(module, "EXPORTED_TOOLS"):
                        category = SKILL_CATEGORIES.get(skill_folder.name, "Other")
                        if category not in tool_index:
                            tool_index[category] = []
                            
                        for tool in module.EXPORTED_TOOLS:
                            # Level 1: Tag tool with category for Holster (v3.1.0)
                            setattr(tool, 'category', category)
                            tools.append(tool)
                            name = getattr(tool, '__name__', str(tool))
                            # Level 1: Meta-Index (1 sentence description)
                            doc = (getattr(tool, '__doc__', '') or 'No description.').strip().split('\n')[0]
                            
                            tool_index[category].append({
                                "name": name,
                                "description": doc,
                                "plugin": skill_folder.name
                            })
                            
                        logger.info("system.skill_loaded", name=skill_folder.name, category=category)
                except Exception as e:
                    logger.error("system.skill_load_error", name=skill_folder.name, error=str(e))
        
        # [v3.7.3] Inject Core System Tools directly into the index for the Planner
        core_tools_category = "System"
        if core_tools_category not in tool_index: tool_index[core_tools_category] = []
        
        # We wrap them so they appear as standard tool objects
        for core_tool, doc_str in [
            (self.switch_workspace, "Shifts consciousness to another project path. Re-indexes everything."),
            (self.hot_reload_skills, "Reloads all tools and manifests without restarting."),
            (self.get_tool_info, "Returns documentation and signature for a specific tool.")
        ]:
            name = core_tool.__name__
            # [v3.7.4 FIX]: Bound methods are immutable; set on __func__ if needed
            try:
                setattr(core_tool, 'category', core_tools_category)
            except AttributeError:
                if hasattr(core_tool, '__func__'):
                    setattr(core_tool.__func__, 'category', core_tools_category)
                else:
                    logger.warning("system.tool_tag_failed", tool=name)
            tools.append(core_tool)
            tool_index[core_tools_category].append({
                "name": name,
                "description": doc_str,
                "plugin": "core"
            })

        return tools, tool_index

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Unified tool execution logic for Router, Brain, and external MCP requests."""
        if tool_name not in self.brain.tool_map:
            # [HEALER v3.6.8] If tool missing, trigger a ONE-TIME hot reload
            logger.warning("system.tool_missing_healing_triggered", tool=tool_name)
            self.hot_reload_skills()
            if tool_name not in self.brain.tool_map:
                return f"Error: Tool '{tool_name}' not found after system reload."
            logger.info("system.tool_recovered", tool=tool_name)
            
        tool_data = self.brain.tool_map[tool_name]
        
        try:
            if tool_data.get("mcp", False):
                # Execute via MCP Bridge
                from agent_skills.mcp_hub.bridge import get_bridge
                bridge = get_bridge()
                return await bridge.call_tool(tool_data["server"], tool_name, arguments)
            else:
                # Execute Native
                func = tool_data["func"]
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    return await func(**arguments)
                return func(**arguments)
        except Exception as e:
            logger.error("system.tool_execution_failed", tool=tool_name, error=str(e))
            return f"[EXECUTION ERROR]: {str(e)}"

    def think(self, user_input: str, source: str = "terminal") -> str:
        """
        Process user input. Applies Firewall checks before delegating to Brain.
        source: 'terminal' | 'telegram:<chat_id>' | 'api'
        """
        from core.security.firewall import axis_firewall, SecurityViolation

        # --- Layer 1: Rate Limiter ---
        if not axis_firewall.is_request_allowed(source=source):
            logger.warning("system.rate_limited", source=source)
            return f"Rate limit exceeded. Maximum {axis_firewall.max_requests} requests per {axis_firewall.window_sec}s. Please wait before sending another command."

        # --- Layer 2: Prompt Injection + Payload Validator ---
        try:
            user_input = axis_firewall.sanitize_input(user_input, source=source)
        except SecurityViolation as e:
            logger.warning("system.security_violation", source=source, error=str(e))
            return f"[SECURITY] Security violation: {e}"

        logger.debug("system.user_input", content=user_input)
        
        # --- NEW: Reset Brain History for NEW Top-Level Task (v3.6.1) ---
        # Robust check to prevent AttributeError if brains are in inconsistent state
        if hasattr(self, 'executor') and hasattr(self.executor, 'reset_history'):
            self.executor.reset_history()
            
        if hasattr(self, 'planner') and hasattr(self.planner, 'reset_history'):
            self.planner.reset_history()
        
        # --- Layer 3: Semantic Router (Fast Track) ---
        fast_response = self.router.route(user_input)
        if fast_response:
            logger.info("system.fast_track_executed")
            return fast_response

        # --- Layer 4: Semantic Caching (RAG 2.0 - March 2026) ---
        cached_plan = None
        if os.getenv("DISABLE_SEMANTIC_CACHE", "false").lower() != "true":
            cached_plan = memory_manager.get_semantic_cache(user_input)
        
        if cached_plan:
            logger.info("system.using_cached_strategy", source="chromadb")
            plan = cached_plan
        else:
            # Generate Strategy via Planner (High-Reasoning - Cloud)
            from core.system.holster import ToolHolster
            filtered_tools = ToolHolster.select_tools(user_input, self.available_tools)
            
            # Level 1: Plan with filtered context
            plan = self.planner.create_plan(user_input, available_tools=filtered_tools)
            # Store in cache for next time (30-40% CPU logic)
            memory_manager.store_semantic_cache(user_input, plan)
        
        if len(plan) > 1:
            logger.info("system.execution_plan_active", steps=len(plan))
            results = [f"Strategic Plan (Cached)" if cached_plan else f"Strategic Plan Created ({len(plan)} steps)"]
        else:
            results = []

        # --- [v3.6.2] INTER-STEP MEMORY ---
        # Accumulate prior step outputs so executor stays grounded across steps.
        prior_context_parts = []

        # 2. Sequential Execution via Executor (Local-First)
        for i, task in enumerate(plan, 1):
            logger.info("system.step_execution", step=i, task=task[:50])
            
            # Build accumulated prior-steps context (last 3 results max)
            prior_context_str = ""
            if prior_context_parts:
                relevant = prior_context_parts[-3:]
                prior_context_str = (
                    "\n\n### CONTEXT FROM PREVIOUS STEPS (use to avoid repeating work):\n"
                    + "\n---\n".join(relevant)
                    + "\n### END CONTEXT\n"
                )
            
            task_prompt = (
                f"EXECUTION STEP {i}/{len(plan)}:{prior_context_str}\n"
                f"Task: {task}\n"
                f"Goal: Complete this specific step. Use the context above to stay grounded "
                f"and avoid re-doing already completed work.\n"
                f"MANDATORY: You MUST call a tool (JSON) to perform this action. If you believe the step is already completed based on prior context, state so clearly and call 'verify_code' or similar to confirm."
            )
            
            step_result = self.executor.think(task_prompt)
            
            # Strip noise and accumulate for future steps
            clean = step_result.replace("MISSION ACCOMPLISHED", "").strip()
            if "[LAST TOOL OUTPUT]:" in clean:
                clean = clean.split("[LAST TOOL OUTPUT]:")[-1].strip()
            if clean:
                prior_context_parts.append(f"[Step {i}: {task[:50]}]\n{clean[:600]}")
            
            if len(plan) > 1:
                results.append(f"--- STEP {i} ---\n{step_result}")
            else:
                results.append(step_result)

        final_response = "\n\n".join(results)
        logger.debug("system.agent_response", content=final_response[:200])
        return final_response

