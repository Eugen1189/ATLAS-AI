import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock dependencies
sys.modules['google.generativeai'] = MagicMock()

import agent_skills.telegram_bridge.listener as listener

class TestTelegramListener(unittest.TestCase):
    @patch('threading.Thread')
    def test_start_telegram_listener(self, mock_thread):
        mock_core = MagicMock()
        listener.start_telegram_listener(mock_core)
        self.assertTrue(mock_thread.called)

    @patch('requests.get')
    @patch('requests.post')
    @patch('time.sleep', return_value=None)
    def test_poll_telegram_loop_break(self, mock_sleep, mock_post, mock_get):
        mock_core = MagicMock()
        
        # We need a way to break the while True loop after one iteration
        # Side effect that raises after some calls
        mock_get.side_effect = [
            MagicMock(json=lambda: {"ok": True, "result": [{"update_id": 1, "message": {"chat": {"id": "123"}, "text": "hi"}}]}),
            KeyboardInterrupt # Break the loop
        ]
        
        with patch('os.getenv', side_effect=lambda k, d=None: "dummy" if k in ["TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"] else d):
            try:
                listener._poll_telegram(mock_core)
            except KeyboardInterrupt:
                pass
        
        self.assertTrue(mock_get.called)
