import unittest
from unittest.mock import patch, MagicMock
import sys

# Mock modules that main depends on
sys.modules['agent_skills.telegram_bridge.listener'] = MagicMock()
sys.modules['google.generativeai'] = MagicMock()

import main

class TestMain(unittest.TestCase):
    @patch('core.i18n.lang.get')
    @patch('main.AxisCore')
    @patch('main.start_telegram_listener')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_boot_sequence_status_exit(self, mock_print, mock_input, mock_tg, mock_core, mock_lang_get):
        mock_lang_get.side_effect = lambda key, **kwargs: f"Mocked {key}"
        mock_input.side_effect = ['status', 'exit']
        
        main.boot_sequence()
        
        self.assertTrue(mock_core.called)
        self.assertTrue(mock_tg.called)
        
        # Verify status message
        mock_print.assert_any_call("\n📊 [SYSTEM] Vision: ONLINE | MCP: 2 SERVERS ACTIVE | TG: CONNECTED\n")

    @patch('core.i18n.lang.get')
    @patch('main.AxisCore')
    @patch('main.start_telegram_listener')
    @patch('builtins.input')
    @patch('builtins.print')
    def test_boot_sequence_unknown_command(self, mock_print, mock_input, mock_tg, mock_core, mock_lang_get):
        mock_lang_get.side_effect = lambda key, **kwargs: f"Mocked {key}"
        mock_input.side_effect = ['something', 'exit']
        
        mock_axis_instance = mock_core.return_value
        mock_axis_instance.think.return_value = "Response"
        
        main.boot_sequence()
        
        mock_axis_instance.think.assert_called_with('something')
        mock_print.assert_any_call("Mocked system.axis_said")

if __name__ == "__main__":
    unittest.main()
