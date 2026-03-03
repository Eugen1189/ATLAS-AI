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

    async def test_shutdown(self):
        self.bridge.exit_stack = AsyncMock()
        await self.bridge.shutdown()
        self.assertTrue(self.bridge.exit_stack.aclose.called)

if __name__ == "__main__":
    unittest.main()
