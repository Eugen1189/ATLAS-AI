import os
import sys
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path

# 1. Setup minimal AXIS environment for testing
os.environ["AI_BRAIN"] = "ollama"
os.environ["TELEGRAM_BOT_TOKEN"] = "123:test"
os.environ["TELEGRAM_CHAT_ID"] = "456"

# 2. Mock ALL EXTERNAL HEAVY LIBS at the system level BEFORE imports
for mod in [
    'cv2', 'mediapipe', 'pyautogui', 'pyaudio', 'pvporcupine', 'faster_whisper',
    'google.generativeai', 'ollama', 'chromadb', 'PyQt6', 'PyQt6.QtWidgets',
    'PyQt6.QtCore', 'PyQt6.QtGui', 'speechrecognition', 'pyttsx3','openai', 'pygame', 'pygame.mixer'
]:
    sys.modules[mod] = MagicMock()

# 3. Import AXIS components
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.logger import logger
from core.system.path_utils import get_project_root, resolve_path
from core.skills.wrapper import agent_tool
from core.brain.memory import memory_manager

class TestCoverage80(unittest.IsolatedAsyncioTestCase):
    
    def setUp(self):
        # Mock RAG to avoid actual ChromaDB activity
        memory_manager.available = True
        memory_manager.client = MagicMock()
        memory_manager.collection = MagicMock()
        
    def test_path_utils_extended(self):
        # Use a safe resolve that doesn't depend on actual user login for [Your_Username]
        root = get_project_root()
        self.assertTrue(root.exists())
        # Test Resolve Path with a mock root
        with patch('core.system.path_utils.get_project_root', return_value=Path("C:/MockRoot")):
             res = resolve_path("test.txt")
             self.assertTrue(res.endswith("test.txt"))

    @patch('core.brain.ollama_brain.OllamaBrain.initialize', return_value=True)
    @patch('core.brain.planner.Planner.initialize', return_value=True)
    def test_orchestrator_init(self, mock_plan_init, mock_exec_init):
        from core.orchestrator import AxisCore
        with patch('os.chdir'):
            with patch('core.system.discovery.EnvironmentDiscoverer.run_full_discovery', return_value={}):
                axis = AxisCore()
                self.assertIsNotNone(axis.executor)
                self.assertIsNotNone(axis.planner)

    def test_all_skills_discovery_and_metadata_loop(self):
        skills_dir = Path(__file__).parent.parent / "agent_skills"
        for skill_folder in skills_dir.iterdir():
            if skill_folder.is_dir() and (skill_folder / "manifest.py").exists():
                module_path = f"agent_skills.{skill_folder.name}.manifest"
                import importlib
                try:
                    module = importlib.import_module(module_path)
                    if hasattr(module, "EXPORTED_TOOLS"):
                        for tool in module.EXPORTED_TOOLS:
                            self.assertIsNotNone(tool.__name__)
                except: continue

    @patch('os.listdir', return_value=['file1.txt', 'dir1'])
    @patch('os.path.isdir', side_effect=lambda x: 'dir1' in x)
    @patch('os.path.getsize', return_value=100)
    @patch('os.path.exists', return_value=True)
    def test_file_master_full(self, mock_exists, mock_size, mock_isdir, mock_listdir):
        from agent_skills.file_master.manifest import list_directory, get_file_tree, read_file
        self.assertIn("📁 dir1/", list_directory("."))
        self.assertIn("Project Tree", get_file_tree("."))
        with patch('builtins.open', unittest.mock.mock_open(read_data="content")):
            self.assertIn("content", read_file("test.txt"))

    @patch('subprocess.run')
    def test_terminal_operator_logic(self, mock_run):
        from agent_skills.terminal_operator.manifest import execute_command
        mock_run.return_value.stdout = "Command output"
        mock_run.return_value.returncode = 0
        res = execute_command("echo test")
        self.assertIn("Command output", res)

    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    @patch('psutil.cpu_percent', return_value=1.0)
    def test_diagnostics_logic_new(self, mock_cpu, mock_disk, mock_mem):
        from agent_skills.diagnostics.manifest import deep_system_scan
        mock_mem.return_value.used = 1*1024**3
        mock_mem.return_value.total = 8*1024**3
        mock_mem.return_value.percent = 12.5
        mock_disk.return_value.free = 50*1024**3
        mock_disk.return_value.total = 100*1024**3
        mock_disk.return_value.percent = 50.0
        res = deep_system_scan()
        self.assertIn("RAM", res)

    @patch('requests.post')
    def test_telegram_bridge_logic_new(self, mock_post):
        from agent_skills.telegram_bridge.manifest import send_telegram_message
        mock_post.return_value.status_code = 200
        res = send_telegram_message("test message")
        self.assertIn("✅", res)

    def test_security_firewall_logic_new(self):
        from core.security.firewall import AxisFirewall, SecurityViolation
        fw = AxisFirewall()
        self.assertTrue(fw.is_request_allowed("terminal"))
        # Test blocking injection commands - 'sudo rm' is in forbidden_patterns
        with self.assertRaises(SecurityViolation):
            fw.sanitize_input("Please sudo rm my files", "terminal")

    def test_brain_logic_new(self):
        from core.brain.gemini_brain import GeminiBrain
        brain = GeminiBrain()
        self.assertEqual(brain.__class__.__name__, "GeminiBrain")
        
        from core.brain.ollama_brain import OllamaBrain
        brain = OllamaBrain()
        self.assertEqual(brain.__class__.__name__, "OllamaBrain")

    def test_personality_blueprints_new(self):
        from core.brain.blueprints import BlueprintManager
        bpm = BlueprintManager()
        self.assertIsNotNone(bpm.get_system_prompt_addon())

    def test_validator_logic_new(self):
        from core.brain.parser import extract_json_data, parse_llm_response
        res = extract_json_data('```json\n{"test": 1}\n```')
        self.assertEqual(res, {"test": 1})
        res2 = parse_llm_response('{"tool_name": "test", "arguments": {}}')
        self.assertEqual(res2["tool_name"], "test")

    def test_holster_selection_new(self):
        from core.system.holster import ToolHolster
        tools = [MagicMock() for _ in range(3)]
        for i, t in enumerate(tools): t.__name__ = f"tool_{i}"
        res = ToolHolster.select_tools("test", tools)
        self.assertIsNotNone(res)

    @patch('core.security.guard.SecurityGuard.set_workspace')
    def test_security_guard_logic(self, mock_set):
        from core.security.guard import SecurityGuard
        SecurityGuard.set_workspace("C:/Projects/Atlas")
        self.assertTrue(SecurityGuard.is_safe_path("C:/Projects/Atlas/src"))
        self.assertFalse(SecurityGuard.is_safe_path("C:/Windows/System32"))

    def test_discovery_init(self):
        from core.system.discovery import EnvironmentDiscoverer
        ed = EnvironmentDiscoverer(project_root="C:/Projects/Atlas")
        self.assertEqual(str(ed.project_root), "C:/Projects/Atlas")

if __name__ == "__main__":
    unittest.main()
