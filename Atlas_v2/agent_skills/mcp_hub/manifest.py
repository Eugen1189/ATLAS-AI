import os
import json
from .bridge import get_bridge
import asyncio

# Костиль для синхронного оркестратора (якщо він ще не повністю Async)
def send_to_mcp_sync(server_name: str, tool_name: str, args_dict: dict):
    """
    Виклик інструменту зовнішнього MCP Сервера з Gemini.
    Ця функція експортується для оркестратора.
    """
    bridge = get_bridge()
    if server_name not in bridge.sessions:
        return f"Error: MCP Server '{server_name}' is not connected."
    
    # Виконуємо асинхронний виклик (тимчасове рішення для потоку)
    session = bridge.sessions[server_name]
    
    async def _call():
        return await session.call_tool(tool_name, arguments=args_dict)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Ми вже в асинхронному циклі
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
