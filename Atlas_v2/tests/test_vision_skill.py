import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock CV2, MediaPipe, pyautogui
sys.modules['cv2'] = MagicMock()
sys.modules['mediapipe'] = MagicMock()
sys.modules['pyautogui'] = MagicMock()
import pyautogui
pyautogui.size.return_value = (1920, 1080)

from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

from agent_skills.vision_eye.manifest import toggle_gestures, capture_visual_context
import agent_skills.vision_eye.logic as vision_logic

class TestVisionSkill(unittest.TestCase):
    @patch('agent_skills.vision_eye.manifest.VisionManager')
    def test_vision_toggle(self, mock_manager_class):
        # We need to control the global _vision_instance in the manifest
        # But for unit test, we just want to see it hit the lines.
        import agent_skills.vision_eye.manifest as manifest
        manifest._vision_instance = None
        result = toggle_gestures(True)
        self.assertIn("Mocked vision.activated", result)
        
        result = toggle_gestures(False)
        self.assertIn("Mocked vision.disabled", result)

    @patch('cv2.VideoCapture')
    def test_vision_manager_init(self, mock_cap):
        mock_cap.return_value.isOpened.return_value = True
        manager = vision_logic.VisionManager()
        manager.hands = MagicMock()
        self.assertIsNotNone(manager)
        manager.stop()

    @patch('cv2.VideoCapture')
    @patch('agent_skills.vision_eye.manifest.VisionManager')
    def test_vision_capture(self, mock_vm, mock_cap):
        mock_inst = mock_vm.return_value
        mock_inst.get_latest_frame.return_value = MagicMock()
        mock_inst.is_running = False
        
        result = capture_visual_context()
        self.assertIn("Mocked vision.photo_taken", result)

if __name__ == "__main__":
    unittest.main()
