import functools
import json
import traceback
import logging
from core.logger import logger

def agent_tool(func):
    """
    Decorator for AXIS Skills. 
    1. Tolerance: Filters out hallucinated arguments (kwargs) to prevent TypeError.
    2. Raw Output: Converts results to clean, model-friendly text strings.
    3. MCP Registration: Automatically exposes tool to the MCP ecosystem.
    """
    from .mcp_registry import mcp_registry
    mcp_registry.register_tool(func)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 1. Tolerance Filter
            import inspect
            sig = inspect.signature(func)
            valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}
            
            # 2. Logic Execution
            result = func(*args, **valid_kwargs)
            
            # 3. Professional Raw Output (Clean Text only)
            if result is None:
                return "✅ [SUCCESS]: Action completed."
            
            if isinstance(result, (list, tuple)):
                return "\n".join(str(i) for i in result)
                
            if isinstance(result, dict):
                # If it's a dictionary, we might want to present it as a clean list of key: value
                return "\n".join(f"{k}: {v}" for k, v in result.items())
            
            return str(result).strip()
            
        except Exception as e:
            logger.error(f"tool.execution_failed", tool=func.__name__, error=str(e))
            # Systemic signals are better for LLM recovery
            return f"🚨 [TOOL ERROR] '{func.__name__}': {str(e)}"
            
    return wrapper
