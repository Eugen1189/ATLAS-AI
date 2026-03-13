import unittest
from unittest.mock import patch, MagicMock
import os
from core.brain import GeminiBrain, OllamaBrain, BrainFactory

class TestBrain(unittest.TestCase):

    @patch('google.generativeai.configure')
    @patch('google.generativeai.GenerativeModel')
    @patch('core.brain.blueprints.BlueprintManager')
    def test_gemini_brain(self, mock_bp, mock_genai_model, mock_genai_config):
        brain = GeminiBrain()
        
        # Test init without API key
        with patch.dict(os.environ, {}, clear=True):
            if "GEMINI_API_KEY" in os.environ:
                del os.environ["GEMINI_API_KEY"]
            self.assertFalse(brain.initialize([]))
            
        # Test init with API key
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"}):
            mock_model = MagicMock()
            mock_genai_model.return_value = mock_model
            
            self.assertTrue(brain.initialize([]))
            mock_genai_config.assert_called_with(api_key="test_key")
            
            # Test think
            brain.chat_session = MagicMock()
            brain.chat_session.send_message.return_value.text = "Response"
            self.assertEqual(brain.think("Hello"), "Response")

    @patch('core.brain.ollama_brain.ollama')
    @patch('core.brain.ollama_brain.BlueprintManager')
    def test_ollama_brain(self, mock_bp):

        def dummy_tool():
            """Dummy Tool"""
            return "Execution result"
            
        brain = OllamaBrain()
        brain.tool_map = {"dummy_tool": dummy_tool}
        
        # Test initialize
        with patch('core.brain.ollama_brain.OLLAMA_AVAILABLE', True):
            brain.client = MagicMock()
            
            # Setup bp manager correctly
            mock_bp_instance = mock_bp.return_value
            mock_bp_instance.get_system_prompt_addon.return_value = "Mocked Addon"
            
            self.assertTrue(brain.initialize([dummy_tool]))
            self.assertIn("Dummy Tool", brain.system_prompt)
            
            # Test check_model_health
            brain.client.list.return_value = {"models": [{"model": "llama3.2:latest"}]}
            brain.model_name = "llama3.2"
            self.assertTrue(brain.check_model_health())
            
            # Test think JSON parsing
            mock_response_tool = {
                'message': {
                    'content': '```json\n{"tool_name": "dummy_tool", "arguments": {}}\n```'
                }
            }
            # Next response after feeding tool output
            mock_response_final = {
                'message': {
                    'content': 'Final answer'
                }
            }
            # Only 2 calls now: one for tool call, one for final answer (no review)
            brain.client.chat.side_effect = [mock_response_tool, mock_response_final]
            
            res = brain.think("test input")
            self.assertEqual(res, "Final answer")
        
        # Test without Ollama
        with patch('core.brain.ollama_brain.OLLAMA_AVAILABLE', False):
            brain.client = None
            self.assertFalse(brain.initialize([]))
            self.assertIn("OFFLINE", brain.think("test"))

    @patch('core.brain.os.getenv')
    def test_brain_factory(self, mock_getenv):
        mock_getenv.return_value = "ollama"
        self.assertIsInstance(BrainFactory.create_brain(), OllamaBrain)
        
        mock_getenv.return_value = "gemini"
        self.assertIsInstance(BrainFactory.create_brain(), GeminiBrain)
        
if __name__ == '__main__':
    unittest.main()
