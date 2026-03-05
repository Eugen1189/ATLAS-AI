import unittest
from unittest.mock import patch, MagicMock
import os
import json
import numpy as np
import tempfile
import shutil

from core.brain.memory import MemoryManager

class TestCoreMemoryManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
        # Patch paths
        self.patcher1 = patch('core.brain.memory.MemoryManager.__init__', return_value=None)
        
        self.patch_dir = patch('os.path.dirname', return_value=self.test_dir)
        
        self.mm = MemoryManager()
        self.mm.memories_dir = self.test_dir
        self.mm.facts_file = os.path.join(self.test_dir, "facts.json")
        self.mm.embeddings_file = os.path.join(self.test_dir, "embeddings.json")
        self.mm.ollama_url = "http://localhost:11434"
        self.mm.embed_model = "test-model"
        self.mm.facts = {}
        self.mm.embeddings = {}

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch('core.brain.memory.requests.post')
    def test_get_embedding_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_post.return_value = mock_resp

        emb = self.mm._get_embedding("test")
        self.assertEqual(emb, [0.1, 0.2, 0.3])
        
    @patch('core.brain.memory.requests.post')
    def test_get_embedding_failure(self, mock_post):
        mock_post.side_effect = Exception("Network error")
        emb = self.mm._get_embedding("test")
        self.assertEqual(emb, [])

    def test_save_and_load_facts(self):
        self.mm.facts = {"test_key": {"value": "test_value", "timestamp": "2026"}}
        self.mm._save_facts()
        
        loaded = self.mm._load_facts()
        self.assertEqual(loaded["test_key"]["value"], "test_value")

    def test_save_and_load_embeddings(self):
        self.mm.embeddings = {"test_key": [0.1, 0.2]}
        self.mm._save_embeddings()
        
        loaded = self.mm._load_embeddings()
        self.assertEqual(loaded["test_key"], [0.1, 0.2])

    @patch('core.brain.memory.MemoryManager._get_embedding')
    @patch('threading.Thread.start')
    def test_store_fact_semantic(self, mock_thread_start, mock_get_emb):
        self.mm.store_fact("key1", "val1", semantic=True)
        self.assertIn("key1", self.mm.facts)
        # Thread should be started
        mock_thread_start.assert_called_once()
        
    def test_store_fact_no_semantic(self):
        self.mm.store_fact("key2", "val2", semantic=False)
        self.assertIn("key2", self.mm.facts)

    @patch('core.brain.memory.MemoryManager._get_embedding')
    def test_semantic_search(self, mock_get_emb):
        # Setup mock embeddings
        self.mm.facts = {"k1": {"value": "v1"}, "k2": {"value": "v2"}}
        self.mm.embeddings = {
            "k1": [1.0, 0.0],
            "k2": [0.0, 1.0]
        }
        # Searching for something similar to k1
        mock_get_emb.return_value = [0.9, 0.1]
        
        results = self.mm.semantic_search("query")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0][0], "k1")
        self.assertEqual(results[1][0], "k2")

    def test_semantic_search_empty(self):
        self.assertEqual(self.mm.semantic_search("query"), [])

    @patch('core.brain.memory.MemoryManager.semantic_search')
    def test_get_context_for_prompt(self, mock_search):
        self.mm.facts = {
            "k1": {"value": "v1", "timestamp": "2026-01-01"},
            "k2": {"value": "v2", "timestamp": "2026-01-02"}
        }
        
        # Test with query
        mock_search.return_value = [("k2", 0.9)]
        ctx = self.mm.get_context_for_prompt(query="test")
        self.assertIn("k2", ctx)
        self.assertNotIn("k1", ctx)
        
        # Test fallback
        ctx_fallback = self.mm.get_context_for_prompt()
        self.assertIn("k1", ctx_fallback)
        self.assertIn("k2", ctx_fallback)

if __name__ == '__main__':
    unittest.main()
