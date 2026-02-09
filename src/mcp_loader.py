import json
import os
import shutil
from typing import List, Dict, Any
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

class MCPLoader:
    def __init__(self, config_path: str = "crewai_mcp.json"):
        self.config_path = config_path

    def load_server(self, server_name: str, tool_names: List[str] = None) -> MCPServerAdapter:
        """
        Loads a specific server by name from the config.
        Optionally filters for specific tools on that server.
        """
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"MCP config file not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            data = json.load(f)

        config = data.get("mcpServers", {}).get(server_name)
        if not config:
            raise ValueError(f"Server '{server_name}' not found in configuration.")

        print(f"Loading Targeted MCP Server: {server_name}")
        
        server_env = config.get("env", {})
        full_env = {**os.environ, **server_env}

        command = config["command"]
        args = config.get("args", [])

        # Resolve relative paths for command and args
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if not os.path.isabs(command) and not shutil.which(command):
             # Try resolving relative to project root
             potential_path = os.path.join(project_root, command)
             if os.path.exists(potential_path):
                 command = potential_path
        
        # Resolve args paths
        resolved_args = []
        for arg in args:
            if isinstance(arg, str) and not os.path.isabs(arg) and (arg.startswith("mcp_servers") or arg.startswith("./mcp_servers")):
                potential_arg = os.path.join(project_root, arg)
                if os.path.exists(potential_arg):
                    resolved_args.append(potential_arg)
                    continue
            resolved_args.append(arg)

        server_params = StdioServerParameters(
            command=command,
            args=resolved_args,
            env=full_env
        )
        
        # MCPServerAdapter takes tool_names in *args (as per our earlier inspection)
        return MCPServerAdapter(server_params, *(tool_names or []))

    def load_servers(self) -> List[MCPServerAdapter]:
        """
        Parses the config JSON and returns a list of configured MCPServerAdapters
        for all enabled servers.
        """
        if not os.path.exists(self.config_path):
            print(f"Warning: MCP config file not found at {self.config_path}")
            return []

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"Error parsing MCP config JSON: {e}")
            return []

        mcp_servers = data.get("mcpServers", {})
        adapters = []

        for name, config in mcp_servers.items():
            if config.get("disabled", False):
                continue
            
            try:
                adapter = self.load_server(name)
                adapters.append(adapter)
            except Exception as e:
                print(f"Failed to initialize adapter for {name}: {e}")

        return adapters

