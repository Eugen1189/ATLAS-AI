import unittest
import os
import tempfile
import shutil

# Mock core.i18n
from core.i18n import lang
from unittest.mock import MagicMock
lang.get = MagicMock(side_effect=lambda key, **kwargs: f"Mocked {key}")

from agent_skills.file_master.manifest import read_file, write_file, list_directory as list_dir

class TestFileMaster(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.test_file = os.path.join(self.test_dir, "test.txt")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_write_and_read_file(self):
        content = "Hello AXIS"
        # Since manifest.py likely uses relative paths or expects a certain structure, 
        # let's test with absolute paths if permitted by the tool design.
        write_file(self.test_file, content)
        
        # Verify file exists
        self.assertTrue(os.path.exists(self.test_file))
        
        # Read file
        read_content = read_file(self.test_file)
        self.assertIn(content, read_content)
        self.assertIn("Start of file", read_content)
        self.assertIn("End of file", read_content)

    def test_list_dir(self):
        # Create a dummy file
        with open(os.path.join(self.test_dir, "file1.txt"), "w") as f:
            f.write("test")
        
        files = list_dir(self.test_dir)
        self.assertIn("file1.txt", files)

    def test_list_dir_not_found(self):
        result = list_dir("/non/existent/path")
        self.assertIn("Mocked file_master.dir_not_found", result)

    def test_read_file_not_found(self):
        result = read_file("/non/existent/file")
        self.assertIn("Mocked file_master.file_not_found", result)

    def test_write_file_error(self):
        # Test writing to an invalid path
        result = write_file("", "content") # Empty path should fail
        self.assertIn("Mocked file_master.file_write_error", result)


if __name__ == "__main__":
    unittest.main()
