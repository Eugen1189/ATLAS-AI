import os
import json
from .bridge import get_bridge
import asyncio
from core.i18n import lang

# Workaround for synchronous orchestrator (if it's not fully Async yet)
def send_to_mcp_sync(server_name: str, tool_name: str, args_dict: dict):
    """
    Call a tool on an external MCP Server from Gemini.
    This function is exported for the orchestrator.
    """
    bridge = get_bridge()
    if server_name not in bridge.sessions:
        return lang.get("mcp.conn_failed", name=server_name, error="Not Connected")
    
    # Execute async call (temporary solution for threading)
    session = bridge.sessions[server_name]
    
    async def _call():
        return await session.call_tool(tool_name, arguments=args_dict)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We are already in an async loop
            import nest_asyncio
            nest_asyncio.apply()
            task = asyncio.ensure_future(_call())
            return loop.run_until_complete(task)
        else:
            return loop.run_until_complete(_call())
    except Exception as e:
        return loop.run_until_complete(_call())

EXPORTED_TOOLS = [
    send_to_mcp_sync
]
