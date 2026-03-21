import unittest
from unittest.mock import MagicMock, patch
import sys
import os
from pathlib import Path

# Setup
for mod in [
    'cv2', 'mediapipe', 'pyautogui', 'pyaudio', 'pvporcupine', 'faster_whisper',
    'google.generativeai', 'ollama', 'chromadb', 'PyQt6', 'PyQt6.QtWidgets',
    'PyQt6.QtCore', 'PyQt6.QtGui', 'speechrecognition', 'pyttsx3','openai', 'pygame', 'pygame.mixer',
    'mcp', 'mcp.server', 'mcp.types'
]:
    sys.modules[mod] = MagicMock()

sys.path.insert(0, str(Path(__file__).parent.parent))

class TestMCPRegistry(unittest.IsolatedAsyncioTestCase):
    
    def test_registry_registration(self):
        # We need to mock the mcp.server.Server class because it's imported at the top level
        from core.skills.mcp_registry import mcp_registry
        
        def dummy_tool(path: str) -> str:
            """Doc."""
            return path
            
        mcp_registry.register_tool(dummy_tool)
        self.assertIn("dummy_tool", mcp_registry.tools)
        
    async def test_registry_call(self):
        from core.skills.mcp_registry import mcp_registry
        
        def dummy_tool(path: str) -> str:
             return f"Path is {path}"
             
        mcp_registry.register_tool(dummy_tool)
        
        # Test the schema generation
        from mcp.types import Tool
        schema = mcp_registry.get_tool_schemas()
        self.assertTrue(len(schema) > 0)
        
        # Test call
        res = await mcp_registry.handle_tool_call("dummy_tool", {"path": "test"})
        self.assertIn("test", res)

if __name__ == "__main__":
    unittest.main()
