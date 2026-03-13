import unittest
from unittest.mock import patch, MagicMock
import sys
import os

from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")
sys.modules['google.generativeai'] = MagicMock()

from core.orchestrator import AxisCore

class TestOrchestrator(unittest.TestCase):
    def setUp(self):
        lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

    @patch("core.orchestrator.BrainFactory.create_brain")
    @patch("core.orchestrator.AxisCore._load_skills")
    def test_init_success(self, mock_load_skills, mock_factory):
        mock_load_skills.return_value = (["tool"], {"Other": [{"name": "tool", "description": "test", "plugin": "test"}]})
        mock_brain = MagicMock()
        mock_brain.initialize.return_value = True
        mock_factory.return_value = mock_brain
        
        core = AxisCore()
        
        self.assertEqual(core.available_tools, ["tool"])
        mock_brain.initialize.assert_called_with(["tool"], tool_index={"Other": [{"name": "tool", "description": "test", "plugin": "test"}]})

    @patch("core.orchestrator.BrainFactory.create_brain")
    @patch("core.orchestrator.AxisCore._load_skills")
    def test_init_failure(self, mock_load_skills, mock_factory):
        mock_brain = MagicMock()
        mock_brain.initialize.return_value = False
        mock_factory.return_value = mock_brain
        
        with self.assertRaises(ValueError):
            AxisCore()

    @patch("core.orchestrator.BrainFactory.create_brain")
    @patch("core.orchestrator.AxisCore._load_skills")
    def test_init_fatal(self, mock_load, mock_factory):
        mock_brain = MagicMock()
        mock_brain.initialize.side_effect = Exception("Fatal")
        mock_factory.return_value = mock_brain
        with self.assertRaises(Exception):
            AxisCore()

    @patch("core.orchestrator.Path.exists")
    @patch("core.orchestrator.BrainFactory.create_brain")
    def test_load_skills_no_dir(self, mock_fac, mock_exists):
        mock_exists.return_value = False
        mock_fac.return_value.initialize.return_value = True
        core = AxisCore()
        self.assertEqual(core.available_tools, [])

    @patch("core.orchestrator.importlib.reload")
    @patch("core.orchestrator.importlib.import_module")
    @patch("core.orchestrator.Path.iterdir")
    @patch("core.orchestrator.Path.exists")
    @patch("core.orchestrator.BrainFactory.create_brain")
    def test_load_skills_with_errors(self, mock_fac, mock_exists, mock_iter, mock_imp, mock_rel):
        mock_exists.return_value = True
        
        # 3 folders: 1 success, 1 import error, 1 general error
        d1, d2, d3, d4 = MagicMock(), MagicMock(), MagicMock(), MagicMock()
        for d in [d1, d2, d3, d4]:
            d.is_dir.return_value = True
            (d / "manifest.py").exists.return_value = True
            
        d1.name = "success_skill"
        d2.name = "import_err"
        d3.name = "gen_err"
        d4.name = "cached_skill"
        
        mock_iter.return_value = [d1, d2, d3, d4]
        
        # Mock sys.modules for d4
        import sys
        import types
        sys.modules["agent_skills.cached_skill"] = types.ModuleType("agent_skills.cached_skill")
        mock_mod = types.ModuleType("agent_skills.cached_skill.manifest")
        sys.modules["agent_skills.cached_skill.manifest"] = mock_mod
        
        try:
            def side_effect(path):
                if "success_skill" in path:
                    m = MagicMock()
                    m.EXPORTED_TOOLS = ["tool1"]
                    return m
                elif "import_err" in path:
                    raise ImportError("missing req")
                elif "gen_err" in path:
                    raise Exception("crash")
                elif "cached_skill" in path:
                    m = MagicMock()
                    m.EXPORTED_TOOLS = ["tool2"]
                    return m
            
            mock_imp.side_effect = side_effect
            
            mock_fac.return_value.initialize.return_value = True
            core = AxisCore()
            
            self.assertIn("tool1", core.available_tools)
        finally:
            if "agent_skills.cached_skill.manifest" in sys.modules:
                del sys.modules["agent_skills.cached_skill.manifest"]
            if "agent_skills.cached_skill" in sys.modules:
                del sys.modules["agent_skills.cached_skill"]
            
    @patch("core.orchestrator.BrainFactory.create_brain")
    @patch("core.orchestrator.AxisCore._load_skills")
    def test_think(self, mock_load, mock_fac):
        mock_load.return_value = (["tool"], {})
        mock_brain = mock_fac.return_value
        mock_brain.initialize.return_value = True
        mock_brain.think.return_value = "response"
        
        core = AxisCore()
        self.assertEqual(core.think("hello"), "response")

if __name__ == "__main__":
    unittest.main()
