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
        self.brain = GeminiBrain()
        self.tool_info = ""
        self.original_index = {}
        self.system_prompt = (
            "You are the AXIS Strategic Planner (v2.9.0). Your job is to analyze the user's request "
            "and create a detailed, optimized step-by-step execution plan.\n\n"
            "AVAILABLE CAPABILITIES:\n{tool_info}\n\n"
            "STRATEGIC RULES:\n"
            "1. Break down complex tasks into atomic, logical steps.\n"
            "2. Ensure each step transitions correctly into the next.\n"
            "3. After receiving tool output, analyze if the task is finished. If yes, move to the next step.\n"
            "4. DO NOT repeat the same tool call with same arguments more than once.\n"
            "5. If a request is ambiguous, add a step to 'Scan and Explore' first.\n"
            "6. [HEALER LOGIC]: If a tool fails due to a missing argument, the next step MUST be to "
            "check the tool documentation (get_tool_info) instead of guessing parameters.\n"
            "7. **STRICT ARGUMENT MAPPING**: For all tools, always use 'path' for file-related tasks (not filepath/file_path) and 'text' for communication or prompts.\n"
            "8. Output exactly a JSON object. No chatter.\n"
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
            
            # Safe access: support both {"plan": [...]} and plain [...]
            if isinstance(data, dict):
                steps = data.get("plan", [])
                # If "plan" key is missing, treat the whole dict as potentially malformed but valid steps if it has items
                if not steps and data:
                    # Alternative: if the model returned something else in JSON
                    # we fall back to user input to be safe
                    steps = [user_input]
            elif isinstance(data, list):
                steps = data
            else:
                steps = []

            if not steps:
                logger.warning("planner.empty_plan", raw=raw_response)
                return [user_input]
            
            logger.info("planner.plan_created", steps_count=len(steps))
            return steps
            
        except Exception as e:
            logger.error("planner.json_failed", error=str(e), raw=raw_response[:200])
            # Emergency Fallback: try to find anything like a list items
            items = re.findall(r"\"(.*?)\"", raw_response)
            # Filter out known keys that might have been caught
            steps = [i for i in items if i.lower() not in ["plan", "steps", "strategy"]]
            return steps if steps else [user_input]

