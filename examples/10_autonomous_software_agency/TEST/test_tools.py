import unittest
import os
import shutil
import tempfile
import sys

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from tools import FileTools

class TestFileTools(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        
    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def test_write_and_read_file(self):
        file_path = os.path.join(self.test_dir, "test.txt")
        content = "Hello, World!"
        
        # Write
        # Access the underlying function or use run
        result = FileTools.write_file.func(file_path, content)
        self.assertIn("Successfully wrote", result)
        
        # Read
        read_content = FileTools.read_file.func(file_path)
        self.assertEqual(read_content, content)
        
    def test_list_files(self):
        os.makedirs(os.path.join(self.test_dir, "subdir"))
        FileTools.write_file.func(os.path.join(self.test_dir, "f1.txt"), "content")
        
        result = FileTools.list_files.func(self.test_dir)
        self.assertIn("subdir", result)
        self.assertIn("f1.txt", result)

    def test_create_directory(self):
        dir_path = os.path.join(self.test_dir, "new_dir")
        result = FileTools.create_directory.func(dir_path)
        self.assertIn("Successfully created", result)
        self.assertTrue(os.path.isdir(dir_path))

if __name__ == "__main__":
    unittest.main()
