import unittest
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil

# Mock core.i18n before importing memory_manager
from core.i18n import lang
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

from agent_skills.memory_manager.manifest import save_to_memory, search_memory
from core.brain.memory import memory_manager

class TestMemoryManager(unittest.TestCase):
    def setUp(self):
        # Mock memory_manager methods
        memory_manager.store_fact = MagicMock()
        memory_manager.get_context_block = MagicMock(return_value="RELEVANT: Test Context")
        memory_manager.get_recent_facts = MagicMock(return_value=[("Key", {"value": "Val", "timestamp": "now"})])
        memory_manager.namespace = "test_ns"

    def tearDown(self):
        pass

    def test_save_and_search_memory(self):
        # Test saving
        topic = "Test Topic"
        fact = "Test Fact"
        result = save_to_memory(topic, fact)
        self.assertIn("[REMEMBERED]: Test Topic", result)

        # Test searching
        search_result = search_memory("Test")
        self.assertIn("RELEVANT: Test Context", search_result)

    def test_search_nothing_found(self):
        memory_manager.get_context_block.return_value = "Nothing here."
        search_result = search_memory("Unknown")
        self.assertIn("[NOT FOUND] in active memory.", search_result)

if __name__ == "__main__":
    unittest.main()
