import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil

# Mock core.i18n before importing memory_manager
from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

from agent_skills.memory_manager.manifest import save_to_memory, search_memory, _init_db

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        # Ensure lang.get is mocked (might have been reset by other tests)
        lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")
        
        # Create a temporary directory for the database
        self.test_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.test_dir, "test_memory.db")
        
        # Patch DB_PATH in the memory_manager module
        self.patcher = patch('agent_skills.memory_manager.manifest.DB_PATH', self.db_path)
        self.patcher.start()
        
        # Initialize the database
        _init_db()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir)

    def test_save_and_search_memory(self):
        # Test saving
        topic = "Test Topic"
        fact = "Test Fact"
        result = save_to_memory(topic, fact)
        self.assertIn("Mocked memory.fact_saved", result)

        # Test searching
        search_result = search_memory("Test")
        self.assertIn("Mocked memory.found", search_result)
        self.assertIn("Test Topic", search_result)
        self.assertIn("Test Fact", search_result)

    def test_search_nothing_found(self):
        search_result = search_memory("Unknown")
        self.assertIn("Mocked memory.nothing_found", search_result)

if __name__ == "__main__":
    unittest.main()
