"""
Unit tests for AXIS RAG Memory System.
Tests VectorStore, CodeIndexer, and RAGRetriever.
"""

import unittest
from unittest.mock import patch, MagicMock, PropertyMock
import os
import json
import tempfile
import shutil


class TestVectorStore(unittest.TestCase):
    """Tests for the ChromaDB VectorStore wrapper."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    @patch("core.brain.vector_store.CHROMADB_AVAILABLE", True)
    @patch("core.brain.vector_store.chromadb")
    def test_init_creates_collection(self, mock_chromadb):
        from core.brain.vector_store import VectorStore

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore(persist_dir=self.test_dir)

        self.assertTrue(store.is_available)
        mock_client.get_or_create_collection.assert_called_once()

    @patch("core.brain.vector_store.CHROMADB_AVAILABLE", False)
    def test_init_without_chromadb(self):
        from core.brain.vector_store import VectorStore
        store = VectorStore(persist_dir=self.test_dir)
        self.assertFalse(store.is_available)

    def test_make_id_deterministic(self):
        from core.brain.vector_store import VectorStore
        id1 = VectorStore._make_id("test_source", 0)
        id2 = VectorStore._make_id("test_source", 0)
        id3 = VectorStore._make_id("test_source", 1)
        self.assertEqual(id1, id2)
        self.assertNotEqual(id1, id3)

    @patch("core.brain.vector_store.CHROMADB_AVAILABLE", True)
    @patch("core.brain.vector_store.chromadb")
    def test_upsert_documents(self, mock_chromadb):
        from core.brain.vector_store import VectorStore

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 0
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore(persist_dir=self.test_dir)

        docs = [
            {
                "text": "def hello(): pass",
                "source": "test.py",
                "chunk_index": 0,
                "metadata": {"type": "python"}
            }
        ]
        store.upsert_documents(docs)
        mock_collection.upsert.assert_called_once()

    @patch("core.brain.vector_store.CHROMADB_AVAILABLE", True)
    @patch("core.brain.vector_store.chromadb")
    def test_query_returns_results(self, mock_chromadb):
        from core.brain.vector_store import VectorStore

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 1
        mock_collection.query.return_value = {
            "documents": [["def hello(): pass"]],
            "metadatas": [[{"source": "test.py", "type": "python"}]],
            "distances": [[0.1]]
        }
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore(persist_dir=self.test_dir)
        results = store.query("hello function")

        self.assertEqual(len(results), 1)
        self.assertIn("text", results[0])
        self.assertIn("source", results[0])
        self.assertIn("score", results[0])

    @patch("core.brain.vector_store.CHROMADB_AVAILABLE", False)
    def test_query_unavailable_returns_empty(self):
        from core.brain.vector_store import VectorStore
        store = VectorStore(persist_dir=self.test_dir)
        results = store.query("test")
        self.assertEqual(results, [])

    @patch("core.brain.vector_store.CHROMADB_AVAILABLE", True)
    @patch("core.brain.vector_store.chromadb")
    def test_get_stats(self, mock_chromadb):
        from core.brain.vector_store import VectorStore

        mock_client = MagicMock()
        mock_collection = MagicMock()
        mock_collection.count.return_value = 42
        mock_client.get_or_create_collection.return_value = mock_collection
        mock_chromadb.PersistentClient.return_value = mock_client

        store = VectorStore(persist_dir=self.test_dir)
        stats = store.get_stats()

        self.assertEqual(stats["status"], "ready")
        self.assertEqual(stats["documents"], 42)


class TestCodeIndexer(unittest.TestCase):
    """Tests for the CodeIndexer."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.is_available = True

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_split_python_file_by_functions(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        content = '''import os

def hello():
    """Say hello."""
    print("hello")

def goodbye():
    """Say goodbye."""
    print("bye")

class MyClass:
    def method(self):
        pass
'''
        chunks = indexer._split_python_file(content, "test.py")
        self.assertGreater(len(chunks), 1)
        # Each chunk should have required fields
        for chunk in chunks:
            self.assertIn("text", chunk)
            self.assertIn("source", chunk)
            self.assertIn("chunk_index", chunk)

    def test_split_markdown_by_headings(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        content = '''# Main Title
Some intro text here.

## Section One
Content for section one.
More content here.

## Section Two
Content for section two.
'''
        chunks = indexer._split_markdown_file(content, "test.md")
        self.assertGreater(len(chunks), 0)

    def test_file_hash_is_deterministic(self):
        from core.brain.code_indexer import CodeIndexer

        test_file = os.path.join(self.test_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello world")

        hash1 = CodeIndexer._file_hash(test_file)
        hash2 = CodeIndexer._file_hash(test_file)
        self.assertEqual(hash1, hash2)

    def test_should_index_detects_changes(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        test_file = os.path.join(self.test_dir, "test.py")
        with open(test_file, "w") as f:
            f.write("# version 1")

        # First time: should index
        self.assertTrue(indexer._should_index(test_file))
        # Second time (same content): should NOT index
        self.assertFalse(indexer._should_index(test_file))

        # After change: should index again
        with open(test_file, "w") as f:
            f.write("# version 2")
        self.assertTrue(indexer._should_index(test_file))

    def test_index_file_skips_unsupported_extensions(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        test_file = os.path.join(self.test_dir, "image.png")
        with open(test_file, "wb") as f:
            f.write(b"\x89PNG\r\n")

        result = indexer.index_file(test_file)
        self.assertEqual(result, 0)

    def test_index_file_processes_python(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        test_file = os.path.join(self.test_dir, "module.py")
        with open(test_file, "w") as f:
            f.write("def greet():\n    return 'hi'\n")

        result = indexer.index_file(test_file, force=True)
        self.assertGreater(result, 0)
        self.mock_vector_store.upsert_documents.assert_called()

    def test_index_directory(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        # Create some test files
        os.makedirs(os.path.join(self.test_dir, "src"))
        with open(os.path.join(self.test_dir, "src", "main.py"), "w") as f:
            f.write("def main(): pass\n")
        with open(os.path.join(self.test_dir, "src", "utils.py"), "w") as f:
            f.write("def helper(): pass\n")
        with open(os.path.join(self.test_dir, "README.md"), "w") as f:
            f.write("# Project\nDescription here.\n")

        stats = indexer.index_directory(self.test_dir, force=True)

        self.assertGreater(stats["files_scanned"], 0)
        self.assertGreater(stats["files_indexed"], 0)
        self.assertGreater(stats["chunks_total"], 0)

    def test_hash_cache_persistence(self):
        from core.brain.code_indexer import CodeIndexer

        os.makedirs(os.path.join(self.test_dir, "memories"), exist_ok=True)
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        indexer.hash_cache = {"file1.py": "abc123"}
        indexer._save_hash_cache()

        indexer2 = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)
        self.assertEqual(indexer2.hash_cache.get("file1.py"), "abc123")


class TestRAGRetriever(unittest.TestCase):
    """Tests for the RAGRetriever."""

    def setUp(self):
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.is_available = True

    def test_retrieve_calls_vector_store(self):
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = [
            {"text": "def foo(): pass", "source": "test.py", "score": 0.9, "metadata": {}}
        ]

        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        results = retriever.retrieve("what is foo?")

        self.assertEqual(len(results), 1)
        self.mock_vector_store.query.assert_called_once()

    def test_retrieve_with_type_filter(self):
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = []
        retriever = RAGRetriever(vector_store=self.mock_vector_store)

        retriever.retrieve("query", doc_type="python")
        call_kwargs = self.mock_vector_store.query.call_args
        self.assertEqual(call_kwargs.kwargs.get("where_filter"), {"type": "python"})

    def test_get_context_block_formats_results(self):
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = [
            {
                "text": "def hello(): return 'world'",
                "source": "Atlas/core/hello.py",
                "score": 0.85,
                "metadata": {"type": "python"}
            }
        ]

        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        block = retriever.get_context_block("hello function")

        self.assertIn("RAG CONTEXT", block)
        self.assertIn("hello", block)
        self.assertIn("85%", block)

    def test_get_context_block_empty_when_no_results(self):
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = []
        retriever = RAGRetriever(vector_store=self.mock_vector_store)

        block = retriever.get_context_block("nonexistent query")
        self.assertEqual(block, "")

    def test_get_context_block_filters_low_scores(self):
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = [
            {"text": "irrelevant", "source": "x.py", "score": 0.1, "metadata": {}}
        ]
        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        block = retriever.get_context_block("query", min_score=0.3)
        self.assertEqual(block, "")

    def test_get_stats(self):
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.get_stats.return_value = {"status": "ready", "documents": 10}
        retriever = RAGRetriever(vector_store=self.mock_vector_store)

        stats = retriever.get_stats()
        self.assertEqual(stats["vector_store"]["documents"], 10)
        self.assertFalse(stats["indexed"])

    def test_ensure_indexed_runs_once(self):
        from core.brain.rag_retriever import RAGRetriever

        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        retriever._indexed = True

        # When already indexed, ensure_indexed() should be a no-op
        retriever.ensure_indexed()
        # _indexed should still be True, no error raised
        self.assertTrue(retriever._indexed)

    def test_index_single_file(self):
        from core.brain.rag_retriever import RAGRetriever

        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        retriever.indexer = MagicMock()
        retriever.indexer.index_file.return_value = 3

        result = retriever.index_single_file("test.py")
        self.assertEqual(result, 3)
        retriever.indexer.index_file.assert_called_with("test.py", force=True)

    def test_get_context_block_shows_line_numbers(self):
        """Context block should include file:line citation from metadata."""
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = [
            {
                "text": "def is_safe(): return True",
                "source": "Atlas/core/security/guard.py",
                "score": 0.92,
                "metadata": {
                    "type": "python",
                    "object_type": "function",
                    "object_name": "SecurityGuard.is_safe_command",
                    "start_line": 29,
                    "end_line": 35,
                }
            }
        ]

        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        block = retriever.get_context_block("is the command safe?")

        self.assertIn("guard.py:29-35", block)
        self.assertIn("function SecurityGuard.is_safe_command", block)
        self.assertIn("92%", block)

    def test_default_threshold_filters_borderline_results(self):
        """Default min_score of 0.45 should filter out marginally relevant chunks."""
        from core.brain.rag_retriever import RAGRetriever

        self.mock_vector_store.query.return_value = [
            {"text": "tangential match", "source": "x.py", "score": 0.40, "metadata": {}},
            {"text": "good match", "source": "y.py", "score": 0.80, "metadata": {}},
        ]
        retriever = RAGRetriever(vector_store=self.mock_vector_store)
        block = retriever.get_context_block("some query")  # default min_score=0.45

        self.assertIn("good match", block)
        self.assertNotIn("tangential", block)


class TestRichMetadata(unittest.TestCase):
    """Tests for the enhanced metadata in CodeIndexer chunks."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.is_available = True

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_detect_python_class(self):
        from core.brain.code_indexer import CodeIndexer
        obj_type, obj_name = CodeIndexer._detect_python_object("class SecurityGuard:")
        self.assertEqual(obj_type, "class")
        self.assertEqual(obj_name, "SecurityGuard")

    def test_detect_python_function(self):
        from core.brain.code_indexer import CodeIndexer
        obj_type, obj_name = CodeIndexer._detect_python_object("def is_safe_command(command: str) -> bool:")
        self.assertEqual(obj_type, "function")
        self.assertEqual(obj_name, "is_safe_command")

    def test_detect_method_with_class_context(self):
        from core.brain.code_indexer import CodeIndexer
        obj_type, obj_name = CodeIndexer._detect_python_object(
            "    def is_safe_path(self, path):", context_class="SecurityGuard"
        )
        self.assertEqual(obj_type, "function")
        self.assertEqual(obj_name, "SecurityGuard.is_safe_path")

    def test_detect_async_function(self):
        from core.brain.code_indexer import CodeIndexer
        obj_type, obj_name = CodeIndexer._detect_python_object("async def fetch_data():")
        self.assertEqual(obj_type, "async_function")
        self.assertEqual(obj_name, "fetch_data")

    def test_python_chunks_have_object_metadata(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        content = (
            "class Guard:\n"
            "    \"\"\"A guard class.\"\"\"\n"
            "    PATTERNS = ['rm -rf']\n"
            "\n"
            "    def check(self):\n"
            "        return True\n"
            "\n"
            "def standalone():\n"
            "    pass\n"
        )
        chunks = indexer._split_python_file(content, "guard.py")

        types = [c["metadata"]["object_type"] for c in chunks]
        names = [c["metadata"]["object_name"] for c in chunks]

        # Class Guard chunk should exist (has docstring + attribute = enough content)
        self.assertIn("class", types)
        self.assertIn("Guard", names)
        # Method should have class prefix
        has_method = any("Guard.check" in n for n in names)
        self.assertTrue(has_method, f"Expected 'Guard.check' in {names}")
        # Standalone function
        self.assertIn("standalone", names)

    def test_markdown_chunks_have_section_metadata(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        content = '''# Overview
This is the main heading content.

## Security
Security details go here with enough content to be indexed.
'''
        chunks = indexer._split_markdown_file(content, "README.md")

        for chunk in chunks:
            self.assertIn("object_type", chunk["metadata"])
            self.assertEqual(chunk["metadata"]["object_type"], "section")
            self.assertIn("start_line", chunk["metadata"])

    def test_line_based_chunks_have_fragment_type(self):
        from core.brain.code_indexer import CodeIndexer
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        content = "\n".join([f"line {i}" for i in range(60)])
        chunks = indexer._split_by_lines(content, "data.json")

        for chunk in chunks:
            self.assertEqual(chunk["metadata"]["object_type"], "fragment")
            self.assertIn("start_line", chunk["metadata"])
            self.assertIn("end_line", chunk["metadata"])


class TestStaleCleanup(unittest.TestCase):
    """Tests for stale source cleanup in CodeIndexer."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.mock_vector_store = MagicMock()
        self.mock_vector_store.is_available = True

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_cleanup_removes_deleted_files(self):
        from core.brain.code_indexer import CodeIndexer

        os.makedirs(os.path.join(self.test_dir, "memories"), exist_ok=True)
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        # Simulate: file was indexed but then deleted
        deleted_path = os.path.join(self.test_dir, "deleted_module.py")
        existing_path = os.path.join(self.test_dir, "existing.py")

        # Create existing file
        with open(existing_path, "w") as f:
            f.write("def keep(): pass")

        # Add both to hash cache (as if they were previously indexed)
        indexer.hash_cache = {
            deleted_path: "hash_of_deleted",
            existing_path: "hash_of_existing",
        }

        removed = indexer.cleanup_stale_sources()

        self.assertEqual(removed, 1)
        # deleted_path should be removed from hash cache
        self.assertNotIn(deleted_path, indexer.hash_cache)
        # existing_path should remain
        self.assertIn(existing_path, indexer.hash_cache)
        # Vector store should have been asked to delete by source
        self.mock_vector_store.delete_by_source.assert_called_once_with(deleted_path)

    def test_cleanup_no_stale_files(self):
        from core.brain.code_indexer import CodeIndexer

        os.makedirs(os.path.join(self.test_dir, "memories"), exist_ok=True)
        indexer = CodeIndexer(self.mock_vector_store, project_root=self.test_dir)

        existing = os.path.join(self.test_dir, "real.py")
        with open(existing, "w") as f:
            f.write("pass")

        indexer.hash_cache = {existing: "somehash"}
        removed = indexer.cleanup_stale_sources()

        self.assertEqual(removed, 0)
        self.mock_vector_store.delete_by_source.assert_not_called()


if __name__ == "__main__":
    unittest.main()
