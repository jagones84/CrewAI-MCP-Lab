# ComfyUI MCP Server Test

This directory contains the integration test for the Local ComfyUI MCP server.

## Overview

The `test_crewai_agent.py` script validates the full pipeline:
1.  **CrewAI Agent** (running in Project Root Venv)
2.  **MCPLoader** (dynamically loaded)
3.  **MCP Server** (running in `../.venv` via `crewai_mcp.json`)
4.  **Mock ComfyUI** (simulated server for testing)

## Prerequisites

- **Root Venv**: `F:\REPOSITORIES\Crewai\venv` (for the Agent)
- **Local Venv**: `../.venv` (for the MCP Server)

## Running the Test

Run from the project root using the **Root Venv**:

```powershell
venv\Scripts\python.exe mcp_servers/comfyui/TEST/test_crewai_agent.py
```

## Validation

The test will:
- Start a Mock ComfyUI server.
- Connect the Agent to the MCP server.
- Generate a dummy image.
- Verify the image creation.
