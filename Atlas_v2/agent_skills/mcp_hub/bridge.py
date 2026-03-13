import json
import os
import subprocess
from contextlib import AsyncExitStack
from core.logger import logger

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    # Level 2 (2026): Memory transport for in-process unified access
    MCP_AVAILABLE = True

except ImportError:
    MCP_AVAILABLE = False
    logger.warning("mcp.library_missing", message="mcp-python-sdk not installed. MCP Hub features will be disabled.")

class MCPBridge:
    def __init__(self):
        self.available = MCP_AVAILABLE
        self.sessions = {}
        self.exit_stack = AsyncExitStack()
        self.server_processes = {}

    def start_mcp_filesystem(self):
        """Direct spawn of filesystem server via subprocess 
        for use inside Vision Eye without requiring async ClientSession"""
        base_path = "C:/Projects/Atlas/memories"  # AXIS project root memories folder
        
        # Use absolute path for npx since Windows PATH might not update in time
        npx_path = "C:\\Program Files\\nodejs\\npx.cmd"
        if not os.path.exists(npx_path):
            npx_path = "npx" # Fallback to standard env variable
            
        # Run via shell=True because npx is a CMD script on Windows
        cmd = [npx_path, "-y", "@modelcontextprotocol/server-filesystem", base_path]
        
        # Run in background
        try:
            process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True
            )
            logger.info("mcp.filesystem_started", path=base_path)
            self.server_processes['filesystem_subprocess'] = process
            return process
        except Exception as e:
            logger.error("mcp.filesystem_start_error", error=str(e))
            return None

    async def connect_from_config(self):
        """Reads config and connects all described servers"""
        if not self.available:
            logger.warning("mcp.config_skip", reason="mcp library not available")
            return

        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if not os.path.exists(config_path):
            logger.warning("mcp.config_not_found", path=config_path)
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        servers = config.get("mcp_servers", {})
        for name, details in servers.items():
            command = details.get("command")
            args = details.get("args", [])
            env = details.get("env", None)
            
            # Add environment variables if any
            if env:
                sys_env = os.environ.copy()
                for k, v in env.items():
                    val = os.getenv(k, v) 
                    if val != "твій_токен_з_env": sys_env[k] = val
                env = sys_env
                
            await self.connect_to_server(name, command, args, env)

    async def connect_to_server(self, name, command, args, env=None):
        """Connects to a specific MCP server and keeps the session open"""
        if not self.available:
            logger.error("mcp.connect_error", name=name, reason="mcp library missing")
            return False

        logger.info("mcp.connecting", name=name, command=command)
        server_params = StdioServerParameters(command=command, args=args, env=env)
        
        try:
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[name] = session
            logger.info("mcp.connected", name=name)
            return True
        except Exception as e:
            logger.error("mcp.server_connection_failed", name=name, error=str(e))
            return False

    async def connect_internal(self):
        """Pairs the internal MCPRegistry with the bridge for unified access."""
        if not self.available: return
        
        from core.skills.mcp_registry import mcp_registry
        # We simulate an MCP connection for internal tools to maintain protocol consistency
        # In a real 2026 standard, this would be a full server-client over loopback or memory
        # For performance, we'll store the registry itself as a 'virtual' session or wrap it
        self.sessions["internal"] = mcp_registry
        logger.info("mcp.internal_connected")

    async def call_tool(self, server_name: str, tool_name: str, arguments: dict) -> str:
        """Unified entry point for calling any tool (Internal or External MCP)"""
        if server_name not in self.sessions:
            return f"Error: MCP Server '{server_name}' not active."
            
        session = self.sessions[server_name]
        
        try:
            # Check if it's the internal registry (virtual session)
            if server_name == "internal":
                # The registry handler we wrote returns TextContent
                results = await session.server._tool_handlers["call"](tool_name, arguments)
                return "\n".join(r.text for r in results)
            
            # External standard MCP session
            result = await session.call_tool(tool_name, arguments=arguments)
            # Standard MCP result extraction
            if hasattr(result, 'content'):
                return "\n".join(c.text for c in result.content if hasattr(c, 'text'))
            return str(result)
        except Exception as e:
            logger.error("mcp.call_failed", server=server_name, tool=tool_name, error=str(e))
            return f"MCP Call Error: {str(e)}"

    async def shutdown(self):
        """Close all MCP connections"""
        await self.exit_stack.aclose()
        self.sessions.clear()
        logger.info("mcp.shutdown_complete")

# Global instance for use in other modules (e.g. Vision)
_bridge_instance = None

def get_bridge():
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MCPBridge()
    return _bridge_instance
