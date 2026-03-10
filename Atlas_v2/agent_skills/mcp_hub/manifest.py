import asyncio
from .bridge import get_bridge

def call_mcp_tool(server: str, tool: str, args: dict) -> str:
    """Standard 2026 Ecosystem Bridge (MCP). Connects to external services (Docker, GitHub, Notion)."""
    bridge = get_bridge()
    if server not in bridge.sessions: return f"Err: MCP Server '{server}' not connected."
    s = bridge.sessions[server]
    async def _do(): return await s.call_tool(tool, arguments=args)
    try:
        import nest_asyncio
        nest_asyncio.apply()
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_do())
    except Exception as e: return f"MCP Call Err: {e}"

def list_mcp_capabilities() -> str:
    """Lists all available servers and their tools via Model Context Protocol."""
    bridge = get_bridge()
    if not bridge.sessions: return "Memory: No MCP servers currently active."
    return f"### Active MCP Ecosystem:\nActive Servers: {list(bridge.sessions.keys())}"

EXPORTED_TOOLS = [call_mcp_tool, list_mcp_capabilities]
