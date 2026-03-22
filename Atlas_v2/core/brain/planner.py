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
            "STRATEGIC RULES:\n"
            "1. DIRECT EXECUTION: If the USER REQUEST is a simple single-action command, your plan should contain exactly ONE step: a descriptive sentence of that action.\n"
            "2. DATA INTEGRITY: When a user provides specific code or content, you MUST preserve it LITERALLY in the plan steps. Do not use placeholders.\n"
            "3. DESCRIPTIVE STEPS: Each step in the 'plan' list must be a natural language instruction (e.g., 'Write the following code to index.html: [CODE]') rather than a function call or code string.\n"
            "4. REPORTING: Every plan MUST end with a step that commands the agent to SHOW or REPORT the final result/output to the user. Never assume the user can see the internal tool output.\n"
            "5. PATH PRECISION: Always use the full absolute path from the task context (e.g., 'C:/Projects/LegalMind/...'). NEVER omit subfolders or assume files are in the root.\n"
            "6. DISK TRUTH: The file system is the only source of truth. The first step MUST be to READ the relevant file(s) from disk using 'read_file'. DO NOT rely on memory.\n"
            "7. PATH VERIFICATION: Use absolute paths. If you are unsure of a file's location, the first step MUST be to use 'list_directory' or 'search_files' to locate it. NEVER guess or assume folder structures.\n"
            "8. EXECUTION OVER REFLECTION: Prioritize steps that execute commands or write files over steps that just 'analyze' or 'message'.\n"
            "9. Output exactly a JSON object. No chatter.\n"
            "10. AUTONOMOUS REPAIR: If a technical error occurs (ModuleNotFoundError, git errors, path issues), the agent MUST solve it autonomously (e.g., pip install, git init, searching directories with 'list_directory') without asking the user for help. If a file is missing, you MUST use 'list_directory' or 'search_files' to find the real path; creating placeholders or searching the web for local errors is STRICTLY FORBIDDEN.\n"
            "11. SCHEMA-FIRST: You are forbidden from guessing database schemas. Use 'get_db_schema' or 'execute_query' with PRAGMA before any queries.\n"
            "12. ARGUMENT INTEGRITY: Every tool call must include all required arguments. If a tool fails due to missing arguments, re-read the tool documentation and call it correctly.\n"
            "13. ZERO-PLACEHOLDER POLICY: You are strictly forbidden from using placeholders or square brackets like '[Insert ...]', '(Future logic)', or '# Code goes here'. Every file you write MUST contain real, synthesized, or analyzed data. If information is missing, your plan MUST include steps to find it via 'google_research' or 'perplexity_search'.\n"
            "14. SYNC-OR-FAIL: After creating or modifying a tool/skill, you MUST call 'hot_reload_skills' to sync the session context. This is non-negotiable.\n"
            "15. IMPACT ANALYSIS: Before refactoring core modules (e.g., core/brain/* or manifest.py), you MUST use 'analyze_impact' to identify downstream dependants. You are responsible for verifying that your changes do not break the whole chain.\n"
            "16. DELTA-CODING: For modifying existing code, ALWAYS use 'apply_ast_patch' to preserve formatting and surrounding logic. This is your primary weapon for codebase precision.\n"
            "17. QA VALIDATION: After applying a patch or modification, you MUST use 'run_qa_tests' to verify that the system still functions correctly. Never assume success without proof.\n"
            "18. META-QUESTIONS: If the user asks a diagnostic question (e.g., 'Do you understand X?'), your plan should be to EXPLAIN your understanding and internal rules using natural language in a report step, rather than performing a dummy action.\n"
            "19. WORKSPACE LOCK: All WRITE operations MUST stay within {workspace_root}. You are allowed to READ information from sibling projects in the same parent directory to gather context or perform environmental inventory.\n"
            "20. DIAGNOSTIC MODE: When diagnosing yourself, the first step MUST be to read your own source code (core/brain/planner.py) to accurately report your current rules.\n"
            "21. VERIFY BEFORE JUMP: If you plan to call 'switch_workspace' to a sibling project or another folder, you MUST first call 'list_directory' on the parent folder ('..') to confirm the exact directory name exists. Guessing project names is strictly forbidden.\n"
            "22. TOOL EXISTENCE GUARD: You MUST ONLY reference tool names that appear in the AVAILABLE CAPABILITIES list above. NEVER invent tool names like 'send_vision_summary', 'execute_external_script', or any other tool not listed. If a capability does not exist, say so in the report step.\n"
            "23. EXPLORATION OVER AUDIT: When asked to 'scan', 'look at', or 'explore' projects, prefer 'list_directory' and 'read_file'. DO NOT use heavy tools like 'find_code_duplicates' or 'audit_dependencies' unless the user explicitly mentions 'auditing', 'similarity', or 'dead code'.\n"
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

