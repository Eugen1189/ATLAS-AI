import asyncio
from .bridge import get_bridge
from core.skills.wrapper import agent_tool

@agent_tool
def call_mcp_tool(server: str, tool: str, args: dict, **kwargs) -> str:
    """Standard 2026 Ecosystem Bridge (MCP). Connects to external services (GitHub, Upstash Context7).
    
    POLICY [Search Resilience]: 
    - If 'context7' server fails to resolve a library, DO NOT STOP. 
    - TRY at least 2 alternative names/versions before fallback.
    - If all fails, return 'no_results' for Perplexity fallback.
    """
    bridge = get_bridge()
    async def _do(): return await bridge.call_tool(server, tool, args)
    try:
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(_do())
        
        # [PROTOCOL 2.8] Resilience Layer: Smart Hints for the Agent
        if server == "context7" and ("Error" in result or "not found" in result.lower()):
            hint = "\n🔍 [RESILIENCE HINT]: Context7 resolution failed. TRY varying the package name (e.g., 'fastapi' -> 'fastapi-pydantic2') or checking for typos. 2 RETRIES MANDATORY before fallback."
            return f"{result}{hint}"
            
        return result
    except Exception as e: return f"MCP Call Err: {e}"

@agent_tool
def list_mcp_capabilities(**kwargs) -> str:
    """Lists all available servers and their tools via Model Context Protocol."""
    bridge = get_bridge()
    if not bridge.sessions: return "Memory: No MCP servers currently active."
    return f"### Active MCP Ecosystem:\nActive Servers: {list(bridge.sessions.keys())}"

@agent_tool
def list_server_tools(server: str, **kwargs) -> str:
    """Lists all tools provided by a specific registered MCP server."""
    bridge = get_bridge()
    async def _do(): return await bridge.list_tools_for_server(server)
    try:
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_do())
    except Exception as e: return f"Discovery Err: {e}"

EXPORTED_TOOLS = [call_mcp_tool, list_mcp_capabilities, list_server_tools]
