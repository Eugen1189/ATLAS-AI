import unittest
from unittest.mock import patch, MagicMock
from core.validator import SecurityValidator, SkillValidator
import os

class TestSecurityValidator(unittest.TestCase):
    
    def test_is_safe_command_safe(self):
        self.assertTrue(SecurityValidator.is_safe_command("echo Hello"))
        self.assertTrue(SecurityValidator.is_safe_command("python script.py"))
        self.assertTrue(SecurityValidator.is_safe_command("npm start"))
        self.assertTrue(SecurityValidator.is_safe_command("git status"))
        
    def test_is_safe_command_unsafe(self):
        self.assertFalse(SecurityValidator.is_safe_command("rm -rf /"))
        self.assertFalse(SecurityValidator.is_safe_command("del /s /q C:"))
        self.assertFalse(SecurityValidator.is_safe_command("powershell -ExecutionPolicy Bypass script.ps1"))
        self.assertFalse(SecurityValidator.is_safe_command("echo safe | mkfs.ext4 /dev/sda1"))
        
    def test_validate_python_syntax_valid(self):
        code = "def foo():\n    return 1"
        self.assertTrue(SecurityValidator.validate_python_syntax(code))
        
    def test_validate_python_syntax_invalid(self):
        code = "def foo()\n    return 1"
        self.assertFalse(SecurityValidator.validate_python_syntax(code))

class TestSkillValidator(unittest.TestCase):
    
    @patch('core.validator.Path.exists')
    @patch('core.validator.subprocess.run')
    def test_validate_skill_success(self, mock_run, mock_exists):
        mock_exists.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Tests passed"
        mock_result.stderr = ""
        mock_run.return_value = mock_result
        
        result = SkillValidator.run_tests("test_skill")
        self.assertTrue(result["success"])
        self.assertEqual(result["output"], "Tests passed")
        
    @patch('core.validator.Path.exists')
    @patch('core.validator.subprocess.run')
    def test_validate_skill_failure(self, mock_run, mock_exists):
        mock_exists.return_value = True
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error"
        mock_run.return_value = mock_result
        
        result = SkillValidator.run_tests("test_skill")
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Error")
        
    @patch('core.validator.Path.exists')
    @patch('core.validator.subprocess.run')
    def test_validate_skill_exception(self, mock_run, mock_exists):
        mock_exists.return_value = True
        mock_run.side_effect = Exception("Crash")
        
        result = SkillValidator.run_tests("test_skill")
        self.assertFalse(result["success"])
        self.assertIn("Crash", result["error"])

    @patch('core.validator.SkillValidator.run_tests')
    def test_validate_skill_tool(self, mock_run_tests):
        # success
        mock_run_tests.return_value = {"success": True, "output": "ok", "error": ""}
        with patch('core.validator.lang.get', return_value="success"):
            from core.validator import validate_skill_tool
            res = validate_skill_tool("test_skill")
            self.assertIn("ok", res)
            self.assertIn("success", res)
            
        # failure
        mock_run_tests.return_value = {"success": False, "output": "out", "error": "err"}
        with patch('core.validator.lang.get', return_value="failed"):
            from core.validator import validate_skill_tool
            res2 = validate_skill_tool("test_skill")
            self.assertIn("err", res2)
            self.assertIn("out", res2)
            self.assertIn("failed", res2)

if __name__ == '__main__':
    unittest.main()
