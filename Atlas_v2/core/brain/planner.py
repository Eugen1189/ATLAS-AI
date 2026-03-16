import json
import re
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

        # [REPAIR]: Disabled silent fallback to prevent reasoning degradation
        # if planner_type == "gemini" and not gemini_key:
        #    logger.warning("planner.fallback", reason="GEMINI_API_KEY missing, falling back to Ollama.")
        #    planner_type = "ollama"

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
            "AVAILABLE CAPABILITIES:\n{tool_info}\n\n"
            "STRATEGIC RULES:\n"
            "1. DIRECT EXECUTION: If the USER REQUEST is a simple single-action command, your plan should contain exactly ONE step: a descriptive sentence of that action.\n"
            "2. DATA INTEGRITY: When a user provides specific code or content, you MUST preserve it LITERALLY in the plan steps. Do not use placeholders.\n"
            "3. DESCRIPTIVE STEPS: Each step in the 'plan' list must be a natural language instruction (e.g., 'Write the following code to index.html: [CODE]') rather than a function call or code string.\n"
            "4. REPORTING: Every plan MUST end with a step that commands the agent to SHOW or REPORT the final result/output to the user. Never assume the user can see the internal tool output.\n"
            "5. PATH PRECISION: Always use the full absolute path from the task context (e.g., 'C:/Projects/LegalMind/...'). NEVER omit subfolders or assume files are in the root.\n"
            "6. DISK TRUTH: If the task involves code logic, the first step MUST be to READ the relevant file(s) from disk using 'read_file'. Do NOT rely on memory summaries.\n"
            "7. EXECUTION OVER REFLECTION: Prioritize steps that execute commands or write files over steps that just 'analyze' or 'message'.\n"
            "8. Output exactly a JSON object. No chatter.\n"
            "9. AUTONOMOUS REPAIR: If a technical error occurs (ModuleNotFoundError, git errors, path issues), the agent MUST solve it autonomously (e.g., pip install, git init, searching directories) without creating steps that ask the user for help. Do not 'message' the user about technical failures unless all autonomous attempts have failed.\n"
            "10. SCHEMA-FIRST: You are forbidden from guessing database column names or table structures. If the task involves SQL or databases, the first database-related step MUST be to use 'get_db_schema' or 'execute_query' with a PRAGMA to verify the structure before performing any meaningful queries.\n"
            "FORMAT: {{\"plan\": [\"step 1\", \"step 2\", ...]}}"
        )

    def initialize(self, tools, index):
        # Build a compact tool index for the planner
        self.original_index = index or {}
        info = []
        for cat, t_list in self.original_index.items():
            t_names = [t['name'] for t in t_list]
            info.append(f"- {cat}: {', '.join(t_names)}")
        self.tool_info = "\n".join(info)
        
        return self.brain.initialize(tools, index)

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
        
        prompt = self.system_prompt.format(tool_info=current_tool_info)
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

