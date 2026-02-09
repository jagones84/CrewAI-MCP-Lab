
import sys
import os
import time
import subprocess
import asyncio
import socket
from crewai import Agent

# Add project root to path to find src.mcp_loader
# We assume this script is in F:/REPOSITORIES/Crewai/mcp_servers/comfyui-dgspark/TEST/
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

print(f"Running Test with Python: {sys.executable}")
print(f"Project Root: {PROJECT_ROOT}")

try:
    from src.mcp_loader import MCPLoader
except ImportError:
    print("Could not import MCPLoader from src.mcp_loader")
    sys.exit(1)

def test_architecture():
    # CONFIGURATION: Set to False to verify against REAL ComfyUI-DGSpark (via Tunnel)
    # The MCP Server itself will handle the tunnel creation if configured correctly.
    USE_MOCK = False 

    mock_proc = None
    if USE_MOCK:
        # We use the ComfyUI Venv for this because it has the required dependencies (websockets, etc)
        comfy_venv_python = os.path.join(PROJECT_ROOT, "mcp_servers", "comfyui", ".venv", "Scripts", "python.exe")
        mock_script = os.path.join(os.path.dirname(__file__), "mock_comfyui.py")
        mock_port = "11002"
        
        if not os.path.exists(comfy_venv_python):
            print(f"Error: ComfyUI Venv Python not found at {comfy_venv_python}")
            sys.exit(1)

        print(f"Starting Mock ComfyUI Server on port {mock_port} using: {comfy_venv_python}")
        mock_proc = subprocess.Popen(
            [comfy_venv_python, mock_script, mock_port],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for mock server to start
        print("Waiting for Mock Server to initialize...")
        time.sleep(5) 
    else:
        print("REAL MODE: Skipping Mock Server. Expecting Real ComfyUI-DGSpark via Tunnel at 127.0.0.1:11002")
        print("Note: The MCP Server (comfy_dgspark_server.py) should establish the tunnel automatically.")

    try:
        # 2. Load Tool from crewai_mcp.json using MCPLoader
        # This will spawn the REAL MCP server using the config in crewai_mcp.json
        print("Loading 'comfyui-dgspark' MCP Tool from crewai_mcp.json...")
        loader = MCPLoader(os.path.join(PROJECT_ROOT, "crewai_mcp.json"))
        
        # We load 'comfyui-dgspark'
        adapter = loader.load_server("comfyui-dgspark")
        print(f"Adapter Loaded: {adapter}")

        # Extract tools
        if hasattr(adapter, 'tools'):
            mcp_tools = adapter.tools
        else:
            mcp_tools = [adapter]

        print(f"Tools extracted from adapter: {mcp_tools}")

        # 3. Create Agent (Verifies compatibility)
        print("Creating CrewAI Agent...")
        agent = Agent(
            role="Test Agent DGSpark",
            goal="Test MCP Remote",
            backstory="Tester",
            tools=mcp_tools, 
            llm="gpt-3.5-turbo", # Dummy LLM
            verbose=True
        )
        print("Agent created successfully.")

        # 4. Verify Tool Availability
        found_tool = None
        for tool in agent.tools:
            print(f"Inspecting tool: {tool.name}")
            if "generate_image" in tool.name:
                found_tool = tool
                break
        
        if not found_tool:
             print("ERROR: generate_image tool not found!")
             sys.exit(1)

        # 5. Execute Tool
        # Using a workflow that is likely to exist or be compatible
        output_image_path = os.path.join(os.path.dirname(__file__), "test_dgspark_output.png")
        if os.path.exists(output_image_path):
            os.remove(output_image_path)

        args = {
            "workflow_name": "image_perfectDeliberate_text_to_image_API.json",
            "prompt": "Test Agent DGSpark Remote",
            "output_path": output_image_path
        }
        print(f"Invoking tool '{found_tool.name}' with args: {args}")
        
        try:
            result = found_tool.run(**args)
        except Exception as e:
            print(f"Direct run with kwargs failed: {e}. Trying JSON string...")
            import json
            result = found_tool.run(json.dumps(args))
        
        print(f"Tool Result: {result}")

        # 6. Assertions
        # Check if file exists
        if os.path.exists(output_image_path):
            print(f"SUCCESS: Image file created at {output_image_path}")
            if os.path.getsize(output_image_path) > 0:
                 print("SUCCESS: Image file is not empty.")
            else:
                 print("FAILURE: Image file is empty.")
                 sys.exit(1)
        else:
            print(f"FAILURE: Image file NOT found at {output_image_path}")
            print("Note: If running in Real Mode, ensure the remote server is accessible and SSH tunnel works.")
            sys.exit(1)

        if "generated" in str(result).lower() or "saved" in str(result).lower():
             print("SUCCESS: Tool execution confirmed generation.")
        else:
             print("WARNING: Tool result message did not explicitly confirm generation, but file check passed (if applicable).")

    finally:
        if mock_proc:
            print("Stopping Mock Server...")
            mock_proc.terminate()
            try:
                mock_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mock_proc.kill()

if __name__ == "__main__":
    test_architecture()
