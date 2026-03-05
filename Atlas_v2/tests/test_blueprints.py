import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil
import yaml
from core.brain.blueprints import BlueprintManager

class TestBlueprintManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch('os.path.dirname', return_value=self.test_dir)
        self.patcher.start()
        self.bp_manager = BlueprintManager()
        self.bp_manager.blueprints_dir = self.test_dir
        
    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)
        
    def test_load_blueprint_existing(self):
        # Create a test blueprint
        bp_path = os.path.join(self.test_dir, "testbp.yaml")
        data = {"name": "TestBot"}
        with open(bp_path, "w") as f:
            yaml.dump(data, f)
            
        bp = self.bp_manager.load_blueprint("testbp")
        self.assertEqual(bp["name"], "TestBot")
        self.assertEqual(self.bp_manager.active_blueprint["name"], "TestBot")
        
    def test_load_blueprint_not_existing_default(self):
        # Should create default if not exists
        bp = self.bp_manager.load_blueprint("default")
        self.assertEqual(bp["name"], "AXIS")
        
        # Check if file was created
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "default.yaml")))

    @patch('core.brain.blueprints.yaml.safe_load')
    def test_load_blueprint_exception(self, mock_load):
        mock_load.side_effect = Exception("Parse error")
        bp_path = os.path.join(self.test_dir, "errbp.yaml")
        with open(bp_path, "w") as f:
            f.write("invalid")
            
        bp = self.bp_manager.load_blueprint("errbp")
        self.assertEqual(bp, {})
        
    def test_get_system_prompt_addon(self):
        self.bp_manager.active_blueprint = {
            "name": "CustomBot",
            "role": "Helper",
            "style": "friendly",
            "system_guidance": "Be nice."
        }
        addon = self.bp_manager.get_system_prompt_addon()
        self.assertIn("CustomBot", addon)
        self.assertIn("Helper", addon)
        self.assertIn("friendly", addon)

    def test_get_system_prompt_addon_empty(self):
        self.bp_manager.active_blueprint = {}
        addon = self.bp_manager.get_system_prompt_addon()
        self.assertEqual(addon, "")

if __name__ == '__main__':
    unittest.main()
