
import sys
import os
import time
import subprocess
import asyncio
from crewai import Agent

# Add project root to path to find src.mcp_loader
# We assume this script is in F:/REPOSITORIES/Crewai/mcp_servers/comfyui/TEST/
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
    # 1. Start Mock ComfyUI Server (Back-end Simulation)
    # CONFIGURATION: Set USE_MOCK to False to test against REAL ComfyUI
    USE_MOCK = False
    
    mock_proc = None
    if USE_MOCK:
        # We use the ComfyUI Venv for this because it has the required dependencies (websockets, etc)
        # and we know it exists.
        comfy_venv_python = os.path.join(PROJECT_ROOT, "mcp_servers", "comfyui", ".venv", "Scripts", "python.exe")
        mock_script = os.path.join(os.path.dirname(__file__), "mock_comfyui.py")
        
        if not os.path.exists(comfy_venv_python):
            print(f"Error: ComfyUI Venv Python not found at {comfy_venv_python}")
            # Fallback to current python if venv missing (unlikely based on context)
            comfy_venv_python = sys.executable

        print(f"Starting Mock ComfyUI Server using: {comfy_venv_python}")
        mock_proc = subprocess.Popen(
            [comfy_venv_python, mock_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for mock server to start
        print("Waiting for Mock Server to initialize...")
        time.sleep(5) 
    else:
        print("REAL MODE: Skipping Mock Server. Expecting Real ComfyUI at 127.0.0.1:8188")
        # Check if ComfyUI is running
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', 8188))
        sock.close()
        if result != 0:
            print("ERROR: ComfyUI is NOT running on 127.0.0.1:8188. Please start ComfyUI to run this test.")
            sys.exit(1)
        print("SUCCESS: Found active ComfyUI instance.")

    try:
        # 2. Load Tool from crewai_mcp.json using MCPLoader
        # This will spawn the REAL MCP server using the config in crewai_mcp.json
        print("Loading MCP Tool from crewai_mcp.json...")
        loader = MCPLoader(os.path.join(PROJECT_ROOT, "crewai_mcp.json"))
        
        # We expect 'comfyui' to be defined in crewai_mcp.json
        # and its 'command' to point to the venv python as configured.
        adapter = loader.load_server("comfyui")
        print(f"Adapter Loaded: {adapter}")

        # we expect the adapter to provide a list of tools.
        # Based on 05_illustrated_book_writer/src/agents/agents.py:
        # self.comfy_tools = self.mcp_loader.load_server(comfy_server).tools
        if hasattr(adapter, 'tools'):
            mcp_tools = adapter.tools
        else:
            # Fallback if adapter is iterable or a tool itself (unlikely based on error)
            mcp_tools = [adapter]

        print(f"Tools extracted from adapter: {mcp_tools}")

        # 3. Create Agent (Verifies compatibility)
        print("Creating CrewAI Agent...")
        agent = Agent(
            role="Test Agent",
            goal="Test MCP",
            backstory="Tester",
            tools=mcp_tools, 
            llm="gpt-3.5-turbo", # Dummy LLM, we won't invoke it for tool test
            verbose=True
        )
        print("Agent created successfully.")

        # 4. Verify Tool Availability
        found_tool = None
        # In CrewAI, if an adapter is passed, it might be in agent.tools list
        # We look for a tool with 'generate_image' in its name
        for tool in agent.tools:
            print(f"Inspecting tool: {tool.name}")
            if "generate_image" in tool.name:
                found_tool = tool
                break
        
        if not found_tool:
            print("WARNING: 'generate_image' tool not found in agent.tools. Checking adapter directly.")
            # Sometimes the adapter itself wraps the tools
            if "generate_image" in adapter.name:
                found_tool = adapter

        if not found_tool:
             print("ERROR: generate_image tool not found!")
             sys.exit(1)

        # 5. Execute Tool
        # We invoke the tool directly to verify the chain:
        # Agent Tool -> MCP Client -> MCP Server (subprocess) -> ComfyUI Backend (Mock subprocess)
        output_image_path = os.path.join(os.path.dirname(__file__), "test_output.png")
        if os.path.exists(output_image_path):
            os.remove(output_image_path)

        args = {
        "workflow_name": "image_perfectDeliberate_text_to_image_API.json",
        "prompt": "Test Architecture Cat",
        "output_path": output_image_path
    }
        print(f"Invoking tool '{found_tool.name}' with args: {args}")
        
        try:
            # CrewAI tools usually take a string or dict. 
            # If it's a structured tool, it might take kwargs.
            # MCPServerAdapter tools usually expect a JSON string if invoked manually via `run`,
            # or kwargs if invoked via `_run`.
            # Let's try passing arguments as kwargs first.
            result = found_tool.run(**args)
        except Exception as e:
            print(f"Direct run with kwargs failed: {e}. Trying JSON string...")
            import json
            result = found_tool.run(json.dumps(args))
        
        print(f"Tool Result: {result}")

        # 6. Assertions
        # Check if file was actually created
        if os.path.exists(output_image_path):
            print(f"SUCCESS: Image file created at {output_image_path}")
            # Verify it's not empty
            if os.path.getsize(output_image_path) > 0:
                 print("SUCCESS: Image file is not empty.")
            else:
                 print("FAILURE: Image file is empty.")
                 sys.exit(1)
        else:
            print(f"FAILURE: Image file NOT found at {output_image_path}")
            sys.exit(1)

        if "generated" in str(result).lower() or "saved to" in str(result).lower():
            print("SUCCESS: Tool execution confirmed generation.")
        else:
            print("FAILURE: Tool output did not confirm generation.")
            sys.exit(1)

    finally:
        if mock_proc:
            print("Stopping Mock Server...")
            mock_proc.terminate()
            try:
                mock_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                mock_proc.kill()
        
        # Also clean up MCP server if MCPLoader doesn't do it automatically (it usually relies on process termination)

if __name__ == "__main__":
    test_architecture()
