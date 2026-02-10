import json
import os
import shutil
from typing import List
from crewai_tools import MCPServerAdapter
from mcp import StdioServerParameters

class MCPLoader:
    def __init__(self, config_path: str = "config/mcp_config.json"):
        # Resolve config path relative to the example root (assuming run from example root or src)
        # We will try to find it
        if os.path.exists(config_path):
            self.config_path = os.path.abspath(config_path)
        else:
             # Try going up one level if we are in src/
            potential_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "mcp_config.json")
            if os.path.exists(potential_path):
                self.config_path = potential_path
            else:
                self.config_path = config_path # Let it fail later if not found

    def load_server(self, server_name: str) -> MCPServerAdapter:
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
        # Base dir is where the config file is
        base_dir = os.path.dirname(self.config_path)
        
        if not os.path.isabs(command) and not shutil.which(command):
             potential_path = os.path.normpath(os.path.join(base_dir, command))
             if os.path.exists(potential_path):
                 command = potential_path
        
        resolved_args = []
        for arg in args:
            if isinstance(arg, str) and not os.path.isabs(arg) and ("server.py" in arg or "/" in arg or "\\" in arg):
                potential_arg = os.path.normpath(os.path.join(base_dir, arg))
                if os.path.exists(potential_arg):
                    resolved_args.append(potential_arg)
                    continue
            resolved_args.append(arg)

        server_params = StdioServerParameters(
            command=command,
            args=resolved_args,
            env=full_env
        )
        
        return MCPServerAdapter(server_params)
