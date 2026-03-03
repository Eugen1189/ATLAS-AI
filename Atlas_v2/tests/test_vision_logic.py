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
import agent_skills.vision_eye.logic as vision_logic

class TestVisionLogic(unittest.TestCase):
    def setUp(self):
        with patch('cv2.VideoCapture') as mock_cap:
            mock_cap.return_value.isOpened.return_value = True
            self.manager = vision_logic.VisionManager()

    def test_processing_worker_with_hands(self):
        self.manager.is_running = True
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        self.manager.frame_queue.put(frame)
        
        # Mock Mediapipe Results
        mock_results = MagicMock()
        mock_hand = MagicMock()
        # Landmark list [id, x, y, z] - but MediaPipe gives objects with .x, .y, .z
        lm_mock = MagicMock()
        lm_mock.x = 0.5
        lm_mock.y = 0.5
        mock_hand.landmark = [lm_mock] * 21
        mock_results.multi_hand_landmarks = [mock_hand]
        mock_results.multi_handedness = None
        
        self.manager.hands.process.return_value = mock_results
        
        with patch('cv2.flip', return_value=frame), \
             patch('cv2.cvtColor', return_value=frame), \
             patch('cv2.resize', return_value=frame), \
             patch('cv2.waitKey', side_effect=[ord('q')]), \
             patch('agent_skills.vision_eye.logic.cv2.cvtColor', return_value=frame):
            self.manager._processing_worker()
            self.assertFalse(self.manager.is_running)

if __name__ == "__main__":
    unittest.main()
