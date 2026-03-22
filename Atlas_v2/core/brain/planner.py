import json
import os
import re
from core.system.path_utils import resolve_path
from core.logger import logger
from .gemini_brain import GeminiBrain

class ExecutionPlan:
    def __init__(self, steps: list):
        self.steps = steps

class Planner:
    """
    High-level reasoning engine (v2.9.0).
    Responsible for breaking down complex user requests into a step-by-step plan.
    Uses Gemini 2.0 Flash as the primary planning brain.
    """
    def __init__(self):
        # [BUNKER v5.5] Adaptive Planning Engine — FORCED GEMINI MODE
        import os
        planner_type = os.getenv("PLANNER_BRAIN", "gemini").lower()
        gemini_key = os.getenv("GEMINI_API_KEY")

        if planner_type == "ollama":
            from .ollama_brain import OllamaBrain
            self.brain = OllamaBrain()
        else:
            from .gemini_brain import GeminiBrain
            self.brain = GeminiBrain()
            
        self.tool_info = ""
        self.original_index = {}
        self.system_prompt = (
            "You are the AXIS Strategic Planner (v2.9.5). Your job is to analyze the user's request "
            "and create a detailed, optimized step-by-step execution plan.\n\n"
            "### IDENTITY ANCHOR:\n- CURRENT_WORKSPACE: {workspace_root}\n- MY_CORE_SKILLS: Atlas_v2/agent_skills/\n- ORCHESTRATOR: Atlas_v2/core/orchestrator.py\n\n- FLUID_TRUST: You can READ information from any sibling project in the same environment. You are only LOCKED to writing files inside {workspace_root}. To modify another project, you MUST use 'switch_workspace'.\n\n"
            "AVAILABLE CAPABILITIES:\n{tool_info}\n\n"
            "STRATEGIC RULES (IRON LAWS):\n"
            "1. FOCUS & DIRECT ACTION: Go DIRECTLY to the target path provided. Root reconnaissance (reading README/main.py) is FORBIDDEN unless requested.\n"
            "2. PRECISION EDITING: Use 'apply_ast_patch' for Python logic. Use 'replace_file_content' for Markdown, SQL, and ENV. Never use 'write_file' to overwrite existing project files.\n"
            "3. ZERO-PLACEHOLDER: No stubs (TODO, [Insert Here]). All output must be PRODUCTION-READY.\n"
            "8. EXECUTION OVER REFLECTION: Prioritize steps that execute commands or write files over steps that just 'analyze' or 'message'.\n"
            "4. OBSERVE FIRST: Use 'list_directory' to verify a path before 'read_file'. Use 'PATH HINTS' from tool errors to correct your direction.\n"
            "5. DISCOVERY LOCK: Environment discovery (refresh_environment_discovery) and repair tools are AUTOMATED. Calling them during a task is FORBIDDEN.\n"
            "6. SECURITY BOUNDARY: No editing of '.axis_session.json' or 'core/' modules. Stay strictly within the current workspace.\n"
            "7. TESTED DELIVERY: Use 'run_qa_tests' after edits. Mission Accomplished requires success proof.\n"
            "8. SCHEMA-FIRST: You are forbidden from guessing database schemas. Use 'get_db_schema' or 'execute_query' with PRAGMA before any queries.\n"
            "FORMAT: {{\"plan\": [\"step 1\", \"step 2\", ...]}}"
        )

    def reset_history(self):
        self.brain.reset_history()

    def initialize(self, tools, index, workspace_root: str = None):
        self.workspace_root = workspace_root or os.getcwd()
        # Build a compact tool index for the planner
        self.original_index = index or {}
        info = []
        for cat, t_list in self.original_index.items():
            t_names = [t['name'] for t in t_list]
            info.append(f"- {cat}: {', '.join(t_names)}")
        self.tool_info = "\n".join(info)
        
        return self.brain.initialize(tools, index, workspace_root=self.workspace_root)

    def _get_filtered_tool_info(self, tools: list) -> str:
        """
        Builds tool info string from a filtered list of tool objects (v3.1.0).
        """
        if not tools:
            return "No tools available."
            
        categories = {}
        for tool in tools:
            cat = getattr(tool, 'category', 'Other')
            name = getattr(tool, '__name__', str(tool))
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(name)
            
        filtered_info = []
        for cat, t_names in categories.items():
            filtered_info.append(f"- {cat}: {', '.join(t_names)}")
                
        return "\n".join(filtered_info)

    def create_plan(self, user_input: str, available_tools: list = None) -> list:
        logger.info("planner.creating_plan", input=user_input[:50])
        
        # Level 1: Context Decoupling (v3.1.0)
        # Only show tools that passed through the Holster
        current_tool_info = self._get_filtered_tool_info(available_tools or [])
        
        # [GROUNDING] Fetch current directory structure to prevent hallucinations
        try:
            from agent_skills.file_master.manifest import list_directory
            dir_listing = list_directory(self.workspace_root, recursive=False)
        except:
            dir_listing = "Listing unavailable."

        prompt = self.system_prompt.format(
            tool_info=current_tool_info, 
            workspace_root=self.workspace_root
        )
        prompt += f"\n\n### GROUND TRUTH (Files in {self.workspace_root}):\n{dir_listing}"
        prompt += f"\n\nUSER REQUEST: {user_input}\n\nPLAN (JSON):"
        
        raw_response = self.brain.think(prompt)
        
        try:
            from .parser import extract_json_data
            data = extract_json_data(raw_response)
            
            steps = []
            # [BUNKER v5.5] Structural Repair Logic
            if not data and raw_response.strip():
                # Attempt to find list items directly if JSON parsing failed
                steps = re.findall(r'"([^"]+)"', raw_response)
                if not steps:
                    logger.warning("planner.empty_plan", raw=raw_response)
                    return [user_input]
            elif isinstance(data, dict):
                steps = data.get("plan", [])
                if not steps and data:
                    steps = [user_input]
            elif isinstance(data, list):
                steps = data
            
            # [REPAIR]: Post-processing to enforce STRICT ARGUMENT MAPPING (Rule 7)
            sanitized_steps = []
            for step in steps:
                # [REPAIR]: Ensure step is a string before replacement (v2.9.7)
                step_str = step if isinstance(step, str) else json.dumps(step)
                s = step_str.replace('"file_path":', '"path":').replace('"filepath":', '"path":').replace('"item_path":', '"path":')
                sanitized_steps.append(s)

            logger.info("planner.plan_created", steps_count=len(sanitized_steps))
            return sanitized_steps
            
        except Exception as e:
            logger.error("planner.json_failed", error=str(e), raw=raw_response[:200])
            return [user_input]

