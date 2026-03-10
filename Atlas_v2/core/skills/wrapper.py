import functools
import json
import traceback
import logging
from core.logger import logger

def agent_tool(func):
    """
    Universal Safety Fuse for AXIS Skills.
    Wraps tool functions to catch exceptions, handle **kwargs, 
    and return structured JSON feedback to the LLM.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 1. Execute the actual tool logic
            result = func(*args, **kwargs)
            
            # 2. If already JSON-like string, return as is
            if isinstance(result, str) and (result.strip().startswith('{') or result.strip().startswith('[')):
                return result
                
            # 3. Standardize output to JSON for the Brain
            return json.dumps({
                "status": "success",
                "tool": func.__name__,
                "content": result
            }, ensure_ascii=False)
            
        except Exception as e:
            # 4. Critical Error Handling (The Safety Fuse)
            error_type = type(e).__name__
            error_details = str(e)
            stack_trace = traceback.format_exc()
            
            logger.error(f"tool.execution_failed", 
                         tool=func.__name__, 
                         error=error_type, 
                         details=error_details)
            
            # Send clear instructions to the LLM on how to proceed
            return json.dumps({
                "status": "error",
                "tool": func.__name__,
                "error_type": error_type,
                "message": f"КРИТИЧНА ПОМИЛКА: {error_details}",
                "SYSTEM_INSTRUCTION": (
                    f"Інструмент '{func.__name__}' зламався. Не намагайся викликати його з тими ж аргументами. "
                    "Перевір синтаксис або спробуй інший підхід (інший інструмент). "
                    "Якщо це системна помилка (наприклад, NameError або TypeError), проінформуй користувача, що в коді скіла є баг."
                )
            }, ensure_ascii=False)
            
    return wrapper
