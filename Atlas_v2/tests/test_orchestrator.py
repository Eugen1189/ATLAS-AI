import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import os

# Mock core.i18n
from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

# Mock google.generativeai
sys.modules['google.generativeai'] = MagicMock()

from core.orchestrator import AxisCore

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        # Ensure lang.get is mocked
        lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch("core.orchestrator.genai.GenerativeModel")
    @patch("core.orchestrator.AxisCore._load_skills")
    def test_init(self, mock_load_skills, mock_gen_model):
        mock_load_skills.return_value = []
        core = AxisCore()
        
        self.assertTrue(mock_gen_model.called)
        self.assertEqual(core.available_tools, [])

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test_key"})
    @patch("core.orchestrator.importlib.import_module")
    @patch("core.orchestrator.Path.iterdir")
    def test_load_skills(self, mock_iterdir, mock_import):
        # Setup mock file structure
        skill_dir = MagicMock()
        skill_dir.is_dir.return_value = True
        skill_dir.name = "test_skill"
        (skill_dir / "manifest.py").exists.return_value = True
        mock_iterdir.return_value = [skill_dir]
        
        # Setup mock module
        mock_module = MagicMock()
        mock_module.EXPORTED_TOOLS = ["tool1"]
        mock_import.return_value = mock_module
        
        core = AxisCore()
        tools = core._load_skills()
        
        self.assertIn("tool1", tools)

if __name__ == "__main__":
    unittest.main()
