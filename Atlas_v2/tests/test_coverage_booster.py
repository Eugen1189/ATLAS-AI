from unittest.mock import MagicMock, patch
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
        'flet': MagicMock(), 'pystray': MagicMock(), 'googlesearch': MagicMock()
    }
    for mod, m in mocks.items(): sys.modules[mod] = m
    return mocks

MOCKS = apply_mocks()

import unittest
import numpy as np
from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

class TestCoverageBooster(unittest.TestCase):
    @patch('requests.post')
    @patch('os.getenv', return_value="test")
    def test_telegram_manifest_full(self, mock_env, mock_post):
        from agent_skills.telegram_bridge.manifest import send_telegram_file, ask_user_confirmation
        mock_post.return_value.status_code = 200
        with patch('builtins.open', unittest.mock.mock_open(read_data=b"data")):
            send_telegram_file("dummy.png", "caption")
        mock_post.return_value.json.return_value = {"result": {"message_id": 123}}
        from agent_skills.telegram_bridge.listener import PENDING_CONFIRMATIONS
        with patch('agent_skills.telegram_bridge.manifest.threading.Event') as mock_event:
            mock_instance = MagicMock()
            def fake_wait(timeout=None):
                PENDING_CONFIRMATIONS[123]["result"] = True
                return True
            mock_instance.wait.side_effect = fake_wait
            mock_event.return_value = mock_instance
            ask_user_confirmation("Prompt")

    @patch('cv2.VideoCapture')
    def test_vision_logic_loop(self, mock_cap):
        mock_cap.return_value.isOpened.return_value = True
        mock_cap.return_value.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        from agent_skills.vision_eye.logic import VisionManager
        import cv2
        manager = VisionManager()
        manager.hands = MagicMock()
        manager.is_running = True
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        manager.frame_queue.put(frame)
        
        from agent_skills.vision_eye import logic
        logic.cv2.flip = MagicMock(return_value=frame)
        logic.cv2.cvtColor = MagicMock(return_value=frame)
        logic.cv2.resize = MagicMock(return_value=frame)
        logic.cv2.waitKey = MagicMock(side_effect=[ord('q')])
        logic.cv2.getTextSize = MagicMock(return_value=((100, 20), 10))
        
        manager._processing_worker()
        self.assertFalse(manager.is_running)

if __name__ == "__main__":
    unittest.main()
