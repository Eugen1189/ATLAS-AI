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

        # 2. Memory Context: Set Namespace
        namespace = "default"
        if primary_workspace:
            # Use folder name as namespace, or a hash if we want more precision
            namespace = os.path.basename(primary_workspace).lower()

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
            exec_success = self.executor.initialize(self.available_tools, tool_index=self.tool_index)
            # Initialize Planner
            plan_success = self.planner.initialize(self.available_tools, self.tool_index)
            
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

        # 6. Register Hot Reload as a system tool
        self.brain.tool_map["hot_reload_skills"] = {"func": self.hot_reload_skills, "mcp": False}

        logger.info("system.core_init_success", 
                    count=len(self.available_tools), 
                    categories=list(self.tool_index.keys()), 
                    namespace=namespace)
    
    def hot_reload_skills(self) -> str:
        """Reloads all skills from agent_skills folder without restarting AXIS."""
        logger.info("system.hot_reload_triggered")
        self.available_tools, self.tool_index = self._load_skills()
        success = self.brain.initialize(self.available_tools, tool_index=self.tool_index)
        if success:
            # Re-register tools that might have been lost
            self.brain.tool_map["hot_reload_skills"] = {"func": self.hot_reload_skills, "mcp": False}
            return f"[HOT RELOAD SUCCESS]: Loaded {len(self.available_tools)} tools across {len(self.tool_index)} categories."
        return "[HOT RELOAD FAILED]: Brain initialization error."

    def _load_skills(self):
        """Scans the agent_skills folder and loads EXPORTED_TOOLS with categorization."""
        tools = []
        tool_index = {} # Categorized meta-info
        
        skills_dir = Path(__file__).parent.parent / "agent_skills"
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        # Default Categories for Smart Sharding
        SKILL_CATEGORIES = {
            "file_master": "Files",
            "terminal_operator": "System",
            "vision_eye": "Media",
            "audio_interface": "Media",
            "diagnostics": "System",
            "memory_manager": "Memory",
            "web_research": "Web",
            "mcp_hub": "System",
            "os_control": "System",
            "telegram_bridge": "System",
            "code_intelligence": "Memory",
            "skill_factory": "System"
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
        
        return tools, tool_index

    async def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Unified tool execution logic for Router, Brain, and external MCP requests."""
        if tool_name not in self.brain.tool_map:
            return f"Error: Tool '{tool_name}' not found."
            
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
        
        # --- Layer 3: Semantic Router (Fast Track) ---
        fast_response = self.router.route(user_input)
        if fast_response:
            logger.info("system.fast_track_executed")
            return fast_response

        # --- Layer 4: Semantic Caching (RAG 2.0 - March 2026) ---
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

        # 2. Sequential Execution via Executor (Local-First)
        for i, task in enumerate(plan, 1):
            logger.info("system.step_execution", step=i, task=task[:50])
            
            # Form task prompt for the executor
            task_prompt = (
                f"EXECUTION STEP {i}/{len(plan)}:\n"
                f"Task: {task}\n"
                f"Goal: Complete this specific step using the tools at your disposal."
            )
            
            step_result = self.executor.think(task_prompt)
            
            if len(plan) > 1:
                results.append(f"--- STEP {i} ---\n{step_result}")
            else:
                results.append(step_result)

        final_response = "\n\n".join(results)
        logger.debug("system.agent_response", content=final_response[:200])
        return final_response
