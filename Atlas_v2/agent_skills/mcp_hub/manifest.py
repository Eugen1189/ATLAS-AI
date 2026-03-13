import asyncio
from .bridge import get_bridge
from core.skills.wrapper import agent_tool

@agent_tool
def call_mcp_tool(server: str, tool: str, args: dict, **kwargs) -> str:
    """Standard 2026 Ecosystem Bridge (MCP). Connects to external services (Docker, GitHub, Notion)."""
    bridge = get_bridge()
    async def _do(): return await bridge.call_tool(server, tool, args)
    try:
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_do())
    except Exception as e: return f"MCP Call Err: {e}"

@agent_tool
def list_mcp_capabilities(**kwargs) -> str:
    """Lists all available servers and their tools via Model Context Protocol."""
    bridge = get_bridge()
    if not bridge.sessions: return "Memory: No MCP servers currently active."
    return f"### Active MCP Ecosystem:\nActive Servers: {list(bridge.sessions.keys())}"

EXPORTED_TOOLS = [call_mcp_tool, list_mcp_capabilities]
