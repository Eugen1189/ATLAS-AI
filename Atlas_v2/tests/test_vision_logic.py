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
    @patch('cv2.VideoCapture')
    def setUp(self, mock_cap):
        mock_cap.return_value.isOpened.return_value = True
        mock_cap.return_value.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        self.manager = vision_logic.VisionManager()
        # Mock hands properly to prevent issues if mediapipe init fails
        self.manager.mp_hands = MagicMock()
        self.manager.mp_draw = MagicMock()
        self.manager.hands = MagicMock()

    @patch('cv2.VideoCapture')
    def test_processing_worker_with_hands(self, mock_cap):
        self.manager.is_running = True
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
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
        
        vision_logic.cv2.flip = MagicMock(return_value=frame)
        vision_logic.cv2.cvtColor = MagicMock(return_value=frame)
        vision_logic.cv2.resize = MagicMock(return_value=frame)
        vision_logic.cv2.waitKey = MagicMock(side_effect=[ord('q')])
        vision_logic.cv2.getTextSize = MagicMock(return_value=((100, 20), 10))
        
        self.manager._processing_worker()
        self.assertFalse(self.manager.is_running)

    def test_get_finger_states(self):
        # Create a mock lm_list with 21 elements [id, x, y]
        # To simulate straight fingers, tips should be far from wrist.
        # Wrist is at (0, 1.0)
        lm_list = [[i, 0.5, 0.5] for i in range(21)]
        # Wrist
        lm_list[0] = [0, 0.5, 1.0]
        
        # Test 1: L-shape (Thumb and Index straight, others bent)
        # Thumb (straight)
        lm_list[2] = [2, 0.5, 0.8] # Pip
        lm_list[4] = [4, 0.5, 0.5] # Tip
        
        # Index (straight)
        lm_list[6] = [6, 0.5, 0.8]
        lm_list[8] = [8, 0.5, 0.5]
        
        # Others (bent - tip closer to wrist than pip)
        for pip_id, tip_id in [(10,12), (14,16), (18,20)]:
            lm_list[pip_id] = [pip_id, 0.5, 0.5]
            lm_list[tip_id] = [tip_id, 0.5, 0.8]
            
        self.assertTrue(self.manager._is_l_shape(lm_list))
        self.assertFalse(self.manager._is_fist(lm_list))
        
        # Test 2: Fist (Thumb straight, others bent)
        # We also just test states in general
        lm_list[8] = [8, 0.5, 0.9] # Bend index finger
        self.assertTrue(self.manager._is_fist(lm_list))

    @patch('cv2.VideoCapture')
    def test_vision_startup_and_stop(self, mock_cap):
        # Simple test to cover start/stop loops completely
        mock_cap.return_value.isOpened.return_value = True
        mock_cap.return_value.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        self.manager.start()
        self.assertTrue(self.manager.is_running)
        self.manager.stop()
        self.assertFalse(self.manager.is_running)

    def test_processing_worker_gestures(self):
        self.manager.is_running = True
        self.manager.hands = MagicMock()
        self.manager.mp_draw = MagicMock()
        self.manager.mp_hands = MagicMock()
        
        # We need to simulate multiple process calls for different gestures
        def mock_process(img):
            mock_res = MagicMock()
            hand1 = MagicMock()
            
            # Setup dummy landmarks
            landmarks = []
            for i in range(21):
                lm = MagicMock()
                lm.x, lm.y = 0.5, 0.5
                landmarks.append(lm)
            
            # To trigger VOLUME_CONTROL (smooth_y < 0.20 * h), make index tip y=0.1
            landmarks[8].y = 0.1
            hand1.landmark = landmarks
            
            mock_res.multi_hand_landmarks = [hand1]
            return mock_res
            
        self.manager.hands.process.side_effect = mock_process
        
        # We must also mock cv2 functions so it doesn't crash on img.shape unpacking
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        import sys
        sys.modules['cv2'].flip.return_value = frame
        sys.modules['cv2'].cvtColor.return_value = frame
        sys.modules['cv2'].resize.return_value = frame
        
        import threading
        t = threading.Thread(target=self.manager._processing_worker)
        t.start()
        
        # Push frame
        self.manager.frame_queue.put(frame)
        
        import time
        time.sleep(0.5)
        
        # Second frame for state transition and sleep gesture coverage
        self.manager.hands.process.side_effect = lambda img: MagicMock(
            multi_hand_landmarks=[MagicMock(landmark=[MagicMock(x=0.5, y=0.5) for _ in range(21)])],
            multi_handedness=[MagicMock(), MagicMock()] # Trigger cross arms check
        )
        self.manager.frame_queue.put(frame)
        time.sleep(0.5)
        
        self.manager.is_running = False
        t.join(timeout=1.0)
        
        self.assertIn(self.manager.state, ["IDLE", "PAUSED", "SCREENSHOT", "ACTIVE", "CLICK", "VOLUME_CONTROL", "MEDIA_CONTROL"])

    @patch('agent_skills.vision_eye.logic.pyautogui.press')
    @patch('agent_skills.vision_eye.logic.pyautogui.moveTo')
    @patch('agent_skills.vision_eye.logic.pyautogui.click')
    @patch('agent_skills.vision_eye.logic.pyautogui.screenshot')
    @patch('agent_skills.telegram_bridge.manifest.send_telegram_file')
    def test_action_worker_cases(self, mock_tg, mock_screenshot, mock_click, mock_moveTo, mock_press):
        self.manager.is_running = True
        
        mock_img = MagicMock()
        mock_screenshot.return_value = mock_img
        
        # Push various events
        self.manager._queue_action("UPDATE_CURSOR", (100, 100, True)) 
        self.manager._queue_action("UPDATE_CURSOR", (100, 100, False))
        self.manager._queue_action("KEY_PRESS", "volumeup")
        self.manager._queue_action("SCREENSHOT", None)
        
        import threading, time
        t = threading.Thread(target=self.manager._action_worker)
        t.start()
        
        time.sleep(0.5)
        self.manager.is_running = False
        t.join(timeout=1.0)
        
        self.assertTrue(mock_press.called)
        self.assertTrue(mock_moveTo.called)

if __name__ == "__main__":
    unittest.main()
