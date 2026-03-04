from unittest.mock import MagicMock, patch, AsyncMock
import sys
import os

def apply_mocks():
    mock_pyautogui = MagicMock()
    mock_pyautogui.size.return_value = (1920, 1080)
    mocks = {
        'cv2': MagicMock(), 'mediapipe': MagicMock(), 'pyautogui': mock_pyautogui,
        'pyaudio': MagicMock(), 'pvporcupine': MagicMock(), 'faster_whisper': MagicMock(),
        'openai': MagicMock(), 'pygame': MagicMock(), 'pygame.mixer': MagicMock(),
        'mcp': MagicMock(), 'mcp.client': MagicMock(), 'mcp.client.stdio': MagicMock(),
        'nest_asyncio': MagicMock(), 'google.generativeai': MagicMock(), 'google.genai': MagicMock(),
        'flet': MagicMock(), 'pystray': MagicMock()
    }
    for mod, m in mocks.items(): sys.modules[mod] = m
    return mocks

MOCKS = apply_mocks()

import unittest
from agent_skills.mcp_hub.bridge import MCPBridge

class TestMcpBridge(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.bridge = MCPBridge()

    @patch('subprocess.Popen')
    def test_start_mcp_filesystem(self, mock_popen):
        mock_popen.return_value = MagicMock()
        with patch('os.path.exists', return_value=True):
            res = self.bridge.start_mcp_filesystem()
            self.assertIsNotNone(res)

    @patch('agent_skills.mcp_hub.bridge.stdio_client')
    @patch('agent_skills.mcp_hub.bridge.ClientSession')
    async def test_connect_to_server(self, mock_client_session, mock_stdio_client):
        # Setup mocks for async context managers
        mock_stdio_cm = AsyncMock()
        mock_stdio_cm.__aenter__.return_value = (MagicMock(), MagicMock())
        mock_stdio_client.return_value = mock_stdio_cm
        
        mock_session_cm = AsyncMock()
        mock_session_instance = AsyncMock(spec=['initialize'])
        mock_session_cm.__aenter__.return_value = mock_session_instance
        mock_client_session.return_value = mock_session_cm

        res = await self.bridge.connect_to_server("test_server", "echo", ["hello"])
        self.assertTrue(res)
        self.assertIn("test_server", self.bridge.sessions)
        self.assertTrue(mock_session_instance.initialize.called)

    @patch('os.path.exists', return_value=True)
    @patch('builtins.open', new_callable=MagicMock)
    @patch('json.load')
    async def test_connect_from_config(self, mock_json_load, mock_open, mock_exists):
        mock_json_load.return_value = {"mcp_servers": {"test": {"command": "echo", "args": [], "env": {"VAR": "VALUE"}}}}
        with patch.object(self.bridge, 'connect_to_server', new_callable=AsyncMock) as mock_connect:
            await self.bridge.connect_from_config()
            self.assertTrue(mock_connect.called)
            mock_connect.assert_called_with("test", "echo", [], {"VAR": "VALUE"})

    async def test_shutdown(self):
        self.bridge.exit_stack = AsyncMock()
        await self.bridge.shutdown()
        self.assertTrue(self.bridge.exit_stack.aclose.called)

if __name__ == "__main__":
    unittest.main()
