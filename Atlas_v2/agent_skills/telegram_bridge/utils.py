import re
import json

def format_telegram_response(raw_result) -> str:
    """
    [v3.8.0] Shared Formatting Engine for Telegram Bridge.
    Filtes out <thought> blocks, JSON artifacts, and mission markers.
    """
    if not raw_result: return ""
    
    text = str(raw_result).strip()
    
    # 1. Strip Thought Blocks (Thinking process)
    text = re.sub(r'<thought>.*?</thought>', '', text, flags=re.DOTALL)
    
    # 2. Extract 'response' from JSON if LLM returned structured output
    # Check both raw JSON and Markdown-wrapped JSON
    json_pattern = r'```json\s*(\{.*?\})\s*```'
    
    # Try parsing if it's pure JSON
    if text.startswith('{'):
        try:
            data = json.loads(text)
            if "response" in data: return str(data["response"]).strip()
        except: pass
        
    # Try finding a markdown block
    match = re.search(json_pattern, text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(1))
            if "response" in data: return str(data["response"]).strip()
        except: pass
        
    # 3. Final cleanup
    # Remove any leftover JSON blocks and mission markers
    text = re.sub(r'```json.*?```', '', text, flags=re.DOTALL)
    text = text.replace("MISSION ACCOMPLISHED", "").strip()
    
    return text
