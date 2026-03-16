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
    
    # 2. Try to find a balanced block (Iterative Balance Finder v3.3.0)
    def _find_balanced(text, start_char, end_char):
        start_idx = text.find(start_char)
        if start_idx == -1: return None
        stack = 0
        in_string = False
        escape = False
        for i in range(start_idx, len(text)):
            char = text[i]
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"':
                in_string = not in_string
                continue
            if not in_string:
                if char == start_char:
                    stack += 1
                elif char == end_char:
                    stack -= 1
                    if stack == 0:
                        return text[start_idx:i+1]
        return None

    # Determine which block to look for based on start_index
    start_char = candidate[start_index]
    end_char = '}' if start_char == '{' else ']'
    
    json_block = _find_balanced(candidate[start_index:], start_char, end_char)
    
    if json_block:
        try:
            return json.loads(json_block, strict=False)
        except:
            pass

    # 3. HEALER REPAIR - Fallback for truncated content (v3.3.1)
    repair_content = content.strip()
    
    # Handle unclosed strings first
    in_string = False
    escape = False
    for char in repair_content:
        if escape: escape = False; continue
        if char == '\\': escape = True; continue
        if char == '"': in_string = not in_string
    
    if in_string:
        repair_content += '"'
    
    # Balanced padding
    open_b = repair_content.count('{')
    close_b = repair_content.count('}')
    open_sq = repair_content.count('[')
    close_sq = repair_content.count(']')
    
    if open_b > close_b: repair_content += '}' * (open_b - close_b)
    if open_sq > close_sq: repair_content += ']' * (open_sq - close_sq)
        
    try:
        # Final attempt with aggressive stripping and repair
        last_idx = max(repair_content.rfind('}'), repair_content.rfind(']'))
        if last_idx != -1:
            return json.loads(repair_content[:last_idx+1], strict=False)
    except Exception as e:
        logger.debug("system.json_repair_failed", error=str(e))

    return None

def parse_llm_response(response_text: str) -> dict | None:
    """
    Aggressively extracts and normalizes a tool call from LLM response (v3.4.2).
    Returns standard format: {"tool_name": str, "arguments": dict}
    """
    if not response_text: return None
    
    data = extract_json_data(response_text)
    
    # [HEALER v3.4.2] Deep Search for tool calls in malformed text
    if not data:
        # Search for pattern: "tool_name": "...", "arguments": { ... }
        match = re.search(r'"tool_name"\s*:\s*"([^"]+)"', response_text)
        if match:
            tool_name = match.group(1)
            # Try to find the arguments block starting after this
            args_match = re.search(r'"arguments"\s*:\s*(\{.*\}|\[.*\])', response_text, re.DOTALL)
            if args_match:
                try:
                    args_str = args_match.group(1)
                    # Attempt to find balanced block manually if JSON fails
                    args = extract_json_data(args_str) or {}
                    return {"tool_name": tool_name, "arguments": args}
                except: pass
            else:
                return {"tool_name": tool_name, "arguments": {}}

    if isinstance(data, dict):
        normalized = _normalize_tool_call(data)
        if normalized:
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
