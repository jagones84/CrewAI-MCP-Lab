# ComfyUI-DGSpark MCP Server Test

This directory contains the integration test for the DGX Spark ComfyUI MCP server.

## Overview

The `test_crewai_agent_dgspark.py` script validates the full pipeline:
1.  **CrewAI Agent** (running in Project Root Venv)
2.  **MCPLoader** (dynamically loaded)
3.  **MCP Server** (running in `../.venv` via `crewai_mcp.json` config)
4.  **SSH Tunnel** (Local 11002 -> Remote 8188, managed automatically or manually)
5.  **ComfyUI on DGX Spark** (generating physical images)

## Prerequisites

1.  **SSH Access**: Ensure you have SSH access to `jagones@10.0.0.1` (or your configured host).
2.  **Manual Tunnel (Optional)**: 
    - The server tries to start the tunnel automatically.
    - If you prefer (or if auto-start fails), run your tunnel script:
      ```cmd
      start /b ssh -L 11002:localhost:8188 jagones@10.0.0.1 -N
      ```
3.  **Venv**: Ensure `../.venv` exists and has dependencies installed.

## Running the Test

Run from the project root using the **Root Venv**:

```powershell
venv\Scripts\python.exe mcp_servers/comfyui-dgspark/TEST/test_crewai_agent_dgspark.py
```

## Validation

The test will:
- Connect to the MCP server.
- Request an image generation using `image_perfectDeliberate_text_to_image_API.json`.
- Verify the image file exists and is not empty.
