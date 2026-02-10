import unittest
import sys
import os
import json
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from utils.mcp_loader import MCPLoader

class TestMCPConnection(unittest.TestCase):
    def test_load_server_config(self):
        loader = MCPLoader()
        self.assertTrue(os.path.exists(loader.config_path))
        
    def test_server_tools_availability(self):
        loader = MCPLoader()
        try:
            adapter = loader.load_server("yfinance")
            self.assertIsNotNone(adapter)
            # In a real scenario we might want to test if it can fetch tools
            # but that requires running the async loop which unittest handles poorly without AsyncTestCase
        except Exception as e:
            self.fail(f"Failed to load server: {e}")

if __name__ == '__main__':
    unittest.main()
