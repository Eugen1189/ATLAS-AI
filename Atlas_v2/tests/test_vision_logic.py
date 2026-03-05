from unittest.mock import MagicMock, patch
import sys

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
        self.manager = vision_logic.VisionManager()
        # Mock hands properly to prevent issues if mediapipe init fails
        self.manager.mp_hands = MagicMock()
        self.manager.mp_draw = MagicMock()
        self.manager.hands = MagicMock()

    def tearDown(self):
        self.manager.is_running = False
        import time
        time.sleep(0.1) # Give threads time to exit cleanly

    def test_processing_worker_with_hands(self):
        self.manager.is_running = True
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        self.manager.frame_queue.put(frame)
        
        # Mock Mediapipe Results
        mock_results = MagicMock()
        mock_hand = MagicMock()
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
        vision_logic.cv2.waitKey = MagicMock(side_effect=lambda x: ord('q') if self.manager.is_running else -1)
        vision_logic.cv2.getTextSize = MagicMock(return_value=((100, 20), 10))
        
        self.manager._processing_worker()
        self.assertFalse(self.manager.is_running)

    def test_get_finger_states(self):
        lm_list = [[i, 0.5, 0.5] for i in range(21)]
        lm_list[0] = [0, 0.5, 1.0] # Wrist
        
        # Test 1: L-shape
        lm_list[2] = [2, 0.5, 0.8]
        lm_list[4] = [4, 0.5, 0.5]
        lm_list[6] = [6, 0.5, 0.8]
        lm_list[8] = [8, 0.5, 0.5]
        for pip_id, tip_id in [(10,12), (14,16), (18,20)]:
            lm_list[pip_id] = [pip_id, 0.5, 0.5]
            lm_list[tip_id] = [tip_id, 0.5, 0.8]
            
        self.assertTrue(self.manager._is_l_shape(lm_list))
        self.assertFalse(self.manager._is_fist(lm_list))
        
        # Test 2: Fist
        lm_list[8] = [8, 0.5, 0.9]
        self.assertTrue(self.manager._is_fist(lm_list))

    @patch('agent_skills.vision_eye.logic.cv2.VideoCapture')
    def test_vision_startup_and_stop(self, mock_cap):
        mock_instance = MagicMock()
        mock_instance.isOpened.return_value = True
        mock_instance.read.return_value = (True, np.zeros((480, 640, 3), dtype=np.uint8))
        mock_cap.return_value = mock_instance
        
        self.manager.start()
        self.assertTrue(self.manager.is_running)
        self.manager.stop()
        self.assertFalse(self.manager.is_running)

    def test_processing_worker_gestures(self):
        self.manager.is_running = True
        self.manager.hands = MagicMock()
        self.manager.mp_draw = MagicMock()
        self.manager.mp_hands = MagicMock()
        
        def mock_process(img):
            mock_res = MagicMock()
            hand1 = MagicMock()
            landmarks = []
            for i in range(21):
                lm = MagicMock()
                lm.x, lm.y = 0.5, 0.5
                landmarks.append(lm)
            landmarks[8].y = 0.1
            hand1.landmark = landmarks
            mock_res.multi_hand_landmarks = [hand1]
            return mock_res
            
        self.manager.hands.process.side_effect = mock_process
        
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        import sys
        sys.modules['cv2'].flip.return_value = frame
        sys.modules['cv2'].cvtColor.return_value = frame
        sys.modules['cv2'].resize.return_value = frame
        sys.modules['cv2'].waitKey.side_effect = lambda x: ord('q') if self.manager.is_running else -1
        sys.modules['cv2'].getTextSize.return_value = ((100, 20), 10)
        
        import threading
        t = threading.Thread(target=self.manager._processing_worker)
        t.start()
        
        self.manager.frame_queue.put(frame)
        
        import time
        time.sleep(0.5)
        
        self.manager.hands.process.side_effect = lambda img: MagicMock(
            multi_hand_landmarks=[MagicMock(landmark=[MagicMock(x=0.5, y=0.5) for _ in range(21)])],
            multi_handedness=[MagicMock(), MagicMock()] 
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
        
        self.manager._queue_action("UPDATE_CURSOR", (100, 100, True)) 
        self.manager._queue_action("UPDATE_CURSOR", (100, 100, False))
        self.manager._queue_action("KEY_PRESS", "volumeup")
        self.manager._queue_action("SCREENSHOT", None)
        
        import threading
        import time
        t = threading.Thread(target=self.manager._action_worker)
        t.start()
        
        time.sleep(0.5)
        self.manager.is_running = False
        t.join(timeout=1.0)
        
        self.assertTrue(mock_press.called)
        self.assertTrue(mock_moveTo.called)

if __name__ == "__main__":
    unittest.main()
