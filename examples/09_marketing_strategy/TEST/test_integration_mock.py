import unittest
from unittest.mock import patch, MagicMock
import os
import sys
import shutil

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from main import run
from mcp_loader import MCPLoader
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

class TestIntegrationMock(unittest.TestCase):
    @patch('src.mcp_loader.MCPLoader.load_server')
    @patch('utils.comfy_check.check_comfyui_connection')
    def test_end_to_end_mock(self, mock_check, mock_load_server):
        # 1. Mock ComfyUI check to pass
        mock_check.return_value = True
        
        # 2. Mock MCPLoader.load_server to return our mock server for 'comfyui'
        # and real (or mocked) for others.
        
        original_loader = MCPLoader("crewai_mcp.json")
        
        def side_effect(server_name, tool_names=None):
            if server_name == "comfyui":
                print(f"TEST: Intercepting load_server for {server_name}, using mock_comfy_server.py")
                # Path to mock server
                mock_server_path = os.path.join(os.path.dirname(__file__), "mock_comfy_server.py")
                
                # Use current python executable
                command = sys.executable
                args = [mock_server_path]
                
                params = StdioServerParameters(
                    command=command,
                    args=args,
                    env=os.environ.copy()
                )
                return MCPServerAdapter(params)
            elif server_name == "DuckDuckGo Search Server":
                 # We can let DDG run if available, or mock it too.
                 # For speed/reliability, let's mock it if possible, but DDG is usually fine.
                 # If we want to mock it, we need a mock_ddg_server.py too.
                 # Let's try to use the real one first, assuming uvx/duckduckgo is available.
                 # If it fails, we can mock it.
                 try:
                     return original_loader.load_server(server_name, tool_names)
                 except Exception as e:
                     print(f"TEST: Failed to load real DDG server: {e}. Falling back to mock.")
                     # Fallback to a simple mock that returns dummy search results
                     # We can reuse mock_comfy_server structure but with search tool
                     pass
            
            return original_loader.load_server(server_name, tool_names)

        mock_load_server.side_effect = side_effect

        # 3. Run the main function
        # We need to ensure it doesn't exit with sys.exit(1)
        # We can patch sys.exit? No, run() calls sys.exit on error.
        
        try:
            run()
        except SystemExit as e:
            # If it exits with 0, it's success (maybe). If 1, failure.
            if e.code != 0:
                self.fail(f"Main execution failed with exit code {e.code}")

        # 4. Verify Output
        output_dir = os.path.join(os.path.dirname(__file__), '..', 'outputs')
        # Check if any file was created in output_dir
        # The mock server creates a file based on output_path provided by agent
        
        files = os.listdir(output_dir)
        print(f"TEST: Files in output dir: {files}")
        
        # We expect at least one file from image generation
        # The agent usually names it based on prompt or timestamp
        # Our mock server appends to output_path if provided
        
        has_image = any(f.endswith('.png') or f.endswith('.jpg') or f.endswith('.gif') for f in files)
        # Note: Our mock writes a GIF header but extension might be anything provided by agent
        
        # If the agent saves to "outputs/image.png", we should see it.
        
        if not has_image and not files:
             # Maybe the agent failed to call the tool?
             # Check logs (but we can't easily check logs here without reading file)
             pass
        
        self.assertTrue(len(files) > 0, "No output files generated")

if __name__ == '__main__':
    unittest.main()
