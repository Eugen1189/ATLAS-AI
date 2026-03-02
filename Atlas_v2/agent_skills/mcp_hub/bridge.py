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
        """Прямий запуск файлового сервера через subprocess 
        для використання всередині Vision Eye без необхідності асинхронного ClientSession"""
        base_path = "C:/Projects/Atlas/memories"
        
        # Використовуємо абсолютний шлях до npx, оскільки Windows PATH може не встигнути оновитися
        npx_path = "C:\\Program Files\\nodejs\\npx.cmd"
        if not os.path.exists(npx_path):
            npx_path = "npx" # Фолбек на звичайну змінну середовища
            
        # Запускаємо через shell=True, оскільки npx це CMD скрипт в Windows
        cmd = [npx_path, "-y", "@modelcontextprotocol/server-filesystem", base_path]
        
        # Запуск у фоні
        try:
            process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, shell=True
            )
            print(f"[MCP] Filesystem Server запущенний (Subprocess) для {base_path}")
            self.server_processes['filesystem_subprocess'] = process
            return process
        except Exception as e:
            print(f"[MCP] Помилка запуску Filesystem Server: {e}")
            return None

    async def connect_from_config(self):
        """Читає конфіг та підключає всі описані сервери"""
        config_path = os.path.join(os.path.dirname(__file__), 'config.json')
        if not os.path.exists(config_path):
            print("⚠️ [MCP Hub]: config.json не знайдено.")
            return

        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        servers = config.get("mcp_servers", {})
        for name, details in servers.items():
            command = details.get("command")
            args = details.get("args", [])
            env = details.get("env", None)
            
            # Додаємо змінні середовища, якщо вони є
            if env:
                sys_env = os.environ.copy()
                for k, v in env.items():
                    val = os.getenv(k, v) 
                    if val != "твій_токен_з_env": sys_env[k] = val
                env = sys_env
                
            await self.connect_to_server(name, command, args, env)

    async def connect_to_server(self, name, command, args, env=None):
        """Підключення до конкретного MCP сервера та збереження сесії відкритою"""
        print(f"🔄 [MCP Hub]: Спроба підключення до {name} ({command} {' '.join(args)})...")
        server_params = StdioServerParameters(command=command, args=args, env=env)
        
        try:
            read, write = await self.exit_stack.enter_async_context(stdio_client(server_params))
            session = await self.exit_stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            
            self.sessions[name] = session
            print(f"✅ [MCP Hub]: Підключено до {name}")
            return True
        except Exception as e:
            print(f"❌ [MCP Hub]: Не вдалося підключитися до {name}. Перевірте чи встановлено {command}.")
            print(f"   Деталі: {e}")
            return False

    async def shutdown(self):
        """Закриття всіх з'єднань MCP"""
        await self.exit_stack.aclose()
        self.sessions.clear()
        print("🛑 [MCP Hub]: Всі сесії закрито.")

# Глобальний інстанс для використання в інших модулях (наприклад, Vision)
_bridge_instance = None

def get_bridge():
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = MCPBridge()
    return _bridge_instance
