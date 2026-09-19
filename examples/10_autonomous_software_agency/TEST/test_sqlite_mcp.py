import unittest
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))
from utils.mcp_loader import MCPLoader

class TestSQLiteMCP(unittest.TestCase):
    def setUp(self):
        # Path to config
        self.config_path = os.path.join(os.path.dirname(__file__), "..", "config", "mcp_config.json")
        self.loader = MCPLoader(self.config_path)
        
    def test_load_server(self):
        try:
            adapter = self.loader.load_server("sqlite")
            self.assertIsNotNone(adapter)
            # We can't easily test connection without running it, which is async/complex in unittest without async support
            # But loading successfully means config is correct and path resolves.
        except Exception as e:
            self.fail(f"Failed to load SQLite MCP: {e}")

if __name__ == "__main__":
    unittest.main()
