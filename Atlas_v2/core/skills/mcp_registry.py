import asyncio
from typing import Dict, Any, Callable
from mcp.server import Server

from core.logger import logger

class MCPRegistry:
    """
    Central registry for AXIS skills exposed via MCP.
    Allows local skills to act as an MCP server.
    """
    def __init__(self):
        self.server = Server("axis-internal-skills")
        self.tools: Dict[str, Callable] = {}
        self._setup_handlers()

    def _setup_handlers(self):
        @self.server.list_tools()
        async def list_tools():
            from mcp.types import Tool, TextContent
            return [
                Tool(
                    name=name,
                    description=func.__doc__ or "No description provided.",
                    inputSchema=self._get_input_schema(func)
                )
                for name, func in self.tools.items()
            ]

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]):
            if name not in self.tools:
                raise ValueError(f"Tool {name} not found")
            
            func = self.tools[name]
            try:
                # Local tools are typically synchronous in Atlas_v2
                if asyncio.iscoroutinefunction(func):
                    result = await func(**arguments)
                else:
                    # Run sync tool in a thread if we want to be safe, 
                    # but for now, simple call is okay in this context
                    result = func(**arguments)
                
                from mcp.types import TextContent
                return [TextContent(type="text", text=str(result))]
            except Exception as e:
                logger.error("mcp.tool_call_error", tool=name, error=str(e))
                from mcp.types import TextContent
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _get_input_schema(self, func: Callable) -> Dict[str, Any]:
        """Generates JSON Schema from function signature."""
        import inspect
        sig = inspect.signature(func)
        schema = {
            "type": "object",
            "properties": {},
            "required": []
        }
        for name, param in sig.parameters.items():
            if name in ["kwargs", "args"]: continue
            
            p_type = "string" # Default
            if param.annotation == int: p_type = "integer"
            elif param.annotation == bool: p_type = "boolean"
            elif param.annotation == float: p_type = "number"
            elif param.annotation == dict: p_type = "object"
            elif param.annotation == list: p_type = "array"
            
            schema["properties"][name] = {"type": p_type}
            if param.default == inspect.Parameter.empty:
                schema["required"].append(name)
        
        return schema

    def register_tool(self, func: Callable):
        name = getattr(func, "__name__", str(func))
        self.tools[name] = func
        logger.debug("mcp.tool_registered", name=name)

# Global registry
mcp_registry = MCPRegistry()
