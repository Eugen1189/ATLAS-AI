import re
import json
from core.logger import logger

def extract_json_data(response_text: str) -> dict | list | None:
    """
    General purpose JSON extractor (v3.2.1). 
    Finds the first '{' or '[' and extracts the balanced block.
    Supports auto-correction of unclosed braces and brackets.
    """
    if not response_text:
        return None
        
    # 1. Strip markdown markers and noise
    candidate = response_text.strip()
    candidate = re.sub(r'```(?:json)?\s*', '', candidate, flags=re.IGNORECASE)
    candidate = re.sub(r'```\s*', '', candidate)
    
    # Find the REAL start of JSON
    brace_start = candidate.find('{')
    bracket_start = candidate.find('[')
    
    if brace_start == -1 and bracket_start == -1:
        return None
        
    start_index = brace_start if (brace_start != -1 and (bracket_start == -1 or brace_start < bracket_start)) else bracket_start
    content = candidate[start_index:]
    
    # 2. Try to find a balanced block using regex
    pattern = r'(?:\{(?:[^{}]|(?:\{(?:[^{}]|(?:\{[^{}]*\}))*\}))*\}|\[(?:[^\[\]]|(?:\[(?:[^\[\]]|(?:\[[^\[\]]*\]))*\]))*\])'
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        try:
            return json.loads(match.group(0), strict=False)
        except:
            pass

    # 3. HEALER REPAIR - Fallback for truncated content
    repair_content = content.strip()
    open_b = repair_content.count('{')
    close_b = repair_content.count('}')
    open_sq = repair_content.count('[')
    close_sq = repair_content.count(']')
    
    if open_b > close_b: repair_content += '}' * (open_b - close_b)
    if open_sq > close_sq: repair_content += ']' * (open_sq - close_sq)
        
    try:
        # Search for the LAST possible closing char after repair
        last_idx = max(repair_content.rfind('}'), repair_content.rfind(']'))
        if last_idx != -1:
            return json.loads(repair_content[:last_idx+1], strict=False)
    except Exception as e:
        logger.debug("system.json_repair_failed", error=str(e))

    return None

def parse_llm_response(response_text: str) -> dict | None:
    """
    Aggressively extracts and normalizes a tool call from LLM response.
    Returns standard format: {"tool_name": str, "arguments": dict}
    """
    data = extract_json_data(response_text)
    if isinstance(data, dict):
        normalized = _normalize_tool_call(data)
        if normalized:
            # Only return normalized tool calls here
            return normalized
    return None

def _normalize_tool_call(data: dict) -> dict | None:
    """Standardizes different tool call naming conventions into a single format."""
    tool_name = (
        data.get("tool_name") or 
        data.get("command") or 
        data.get("name") or 
        data.get("tool") or 
        data.get("action") or
        data.get("call")
    )
    
    arguments = (
        data.get("arguments") or 
        data.get("args") or 
        data.get("parameters") or 
        data.get("kwargs") or 
        {}
    )
    
    if tool_name and isinstance(tool_name, str):
        return {"tool_name": tool_name, "arguments": arguments}
    
    return None
