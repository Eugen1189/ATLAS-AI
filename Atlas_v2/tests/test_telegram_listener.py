import unittest
from unittest.mock import MagicMock, patch
import sys

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

    @patch('requests.get')
    @patch('requests.post')
    @patch('time.sleep', return_value=None)
    def test_poll_telegram_callback_and_voice(self, mock_sleep, mock_post, mock_get):
        mock_core = MagicMock()
        mock_core.think.side_effect = ["Standard Reply", Exception("Quota test error"), Exception("Generic error")]
        
        # Configure the global dictionary
        listener.PENDING_CONFIRMATIONS = {100: {"event": MagicMock(), "result": None}}
        
        # Side effects for get
        mock_get.side_effect = [
            MagicMock(json=lambda: {"ok": True, "result": [
                # 1. Voice Message
                {"update_id": 2, "message": {"message_id": 200, "chat": {"id": "123"}, "voice": {"duration": 5}}},
                # 2. Callback Query "yes"
                {"update_id": 3, "callback_query": {"id": "cb1", "data": "confirm_yes", "message": {"message_id": 100, "chat": {"id": "123"}, "text": "Are you sure?"}}},
                # 3. Callback Query "no"
                {"update_id": 4, "callback_query": {"id": "cb2", "data": "confirm_no", "message": {"message_id": 101, "chat": {"id": "123"}, "text": "Another?"}}},
                # 4. Text Message
                {"update_id": 5, "message": {"message_id": 201, "chat": {"id": "123"}, "text": "regular text"}},
                # 5. Text Message (Quota error)
                {"update_id": 6, "message": {"message_id": 202, "chat": {"id": "123"}, "text": "error trigger"}},
                # 6. Text Message (Generic error)
                {"update_id": 7, "message": {"message_id": 203, "chat": {"id": "123"}, "text": "generic error"}},
            ]}),
            KeyboardInterrupt # Break the loop
        ]
        
        def mock_getenv(k, d=None):
            if k == "TELEGRAM_BOT_TOKEN": return "dummy"
            if k == "TELEGRAM_CHAT_ID": return "123"
            return d
            
        with patch('os.getenv', side_effect=mock_getenv):
            try:
                listener._poll_telegram(mock_core)
            except KeyboardInterrupt:
                pass
        
        self.assertTrue(mock_post.called)
        self.assertTrue(listener.PENDING_CONFIRMATIONS[100]["result"])

    @patch('agent_skills.telegram_bridge.manifest.requests.post')
    def test_manifest_functions(self, mock_post):
        from agent_skills.telegram_bridge.manifest import send_telegram_message, send_telegram_photo, ask_user_confirmation
        
        def mock_getenv(k, d=None):
            if k == "TELEGRAM_BOT_TOKEN": return "dummy"
            if k == "TELEGRAM_CHAT_ID": return "123"
            return d
            
        with patch('os.getenv', side_effect=mock_getenv):
            # 1. Message error
            mock_post.return_value.status_code = 500
            send_telegram_message("Hello")
            
            mock_post.side_effect = Exception("Conn Error")
            send_telegram_message("Hello")
            
            # 2. File error
            with patch('builtins.open', new_callable=MagicMock):
                mock_post.side_effect = None
                mock_post.return_value.status_code = 500
                send_telegram_photo("test.png")
                
                mock_post.side_effect = Exception("File Error")
                send_telegram_photo("test.jpg")
                
            # 3. Confirmation error
            mock_post.side_effect = None
            mock_post.return_value.status_code = 500
            mock_post.return_value.json.return_value = {} # Ensure msg_id is None
            ask_user_confirmation("Are you sure?")
            
            mock_post.side_effect = Exception("Confirm Error")
            ask_user_confirmation("Are you sure?")
            
            # 4. Confirmation Timeout
            mock_post.side_effect = None
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"result": {"message_id": 999}}
            
            with patch('threading.Event.wait', return_value=False):
                ask_user_confirmation("Timeout test")
