import asyncio
import json
import os
import subprocess
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

class MCPBridge:
    def __init__(self):
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
            print(f"[MCP] Filesystem Server started (Subprocess) for {base_path}")
            self.server_processes['filesystem_subprocess'] = process
            return process
        except Exception as e:
            print(f"[MCP] Error starting Filesystem Server: {e}")
            return None

    async def connect_from_config(self):
        """Reads config and connects all described servers"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if not os.path.exists(config_path):
            print("⚠️ [MCP Hub]: config.json not found.")
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
        print(f"🔄 [MCP Hub]: Expected connection to {name} ({command} {' '.join(args)})...")
        server_params = StdioServerParameters(command=command, args=args, env=env)
        
        try:
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[name] = session
            print(f"✅ [MCP Hub]: Connected to {name}")
            return True
        except Exception as e:
            print(f"❌ [MCP Hub]: Failed to connect to {name}. Check if {command} is installed.")
            print(f"   Details: {e}")
            return False

    async def shutdown(self):
        """Close all MCP connections"""
        await self.exit_stack.aclose()
        self.sessions.clear()
        print("🛑 [MCP Hub]: All sessions closed.")

# Global instance for use in other modules (e.g. Vision)
_bridge_instance = None

def get_bridge():
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MCPBridge()
    return _bridge_instance
