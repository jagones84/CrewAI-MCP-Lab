# Example 09: Marketing Strategy Campaign

This example demonstrates a multi-modal agentic workflow that combines **Market Research** (Search), **Creative Strategy** (LLM), and **Visual Design** (Image Generation via ComfyUI).

## Overview

The crew consists of three agents:
1.  **Senior Market Researcher**: Uses `DuckDuckGo Search` to analyze the market and competitors.
2.  **Creative Marketing Strategist**: Synthesizes research into a cohesive campaign strategy with taglines.
3.  **AI Visual Designer**: Generates a concept image for the campaign using `ComfyUI`.

## Prerequisites

-   **Python 3.10+**
-   **Node.js** (for MCP servers)
-   **ComfyUI** (running locally or remote)
-   **CrewAI** & **MCP** dependencies

## Configuration

1.  **Environment Variables**:
    Copy `.env.example` to `.env` in the project root and fill in your API keys (OpenAI/OpenRouter).

2.  **LLM Selection**:
    Edit `config/preferences.yaml` to switch between OpenAI, Ollama, or LlamaCpp.

    **Ollama**:
    ```yaml
    llm:
      provider: "ollama"
      ollama:
        model: "llama3"
        # Optional: Path to ollama executable if not in PATH
        executable_path: "C:\\Path\\To\\ollama.exe" 
    ```

    **LlamaCpp**:
    ```yaml
    llm:
      provider: "llamacpp"
      llamacpp:
        model: "llama-3-8b-instruct.gguf"
        models_dir: "C:\\AI\\models"
        executable_path: "C:\\AI\\llama.cpp\\llama-server.exe"
    ```
    
    The example will automatically start and stop the local server for you.

3.49→3.  **ComfyUI**:
50→    You can manually start ComfyUI at `http://127.0.0.1:8188`, OR configure the example to auto-start it:
51→    
52→    Edit `config/preferences.yaml`:
53→    ```yaml
54→    comfyui:
55→      install_path: "C:\\Path\\To\\ComfyUI"
56→      # host: "127.0.0.1" (default)
57→      # port: 8188 (default)
58→    ```
59→    If `install_path` is set and port 8188 is closed, the example will attempt to launch ComfyUI automatically.
60→
61→    If using a custom workflow, ensure it is in `mcp_servers/comfyui/workflow_files/`.

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
python src/main.py
```

## Outputs

The crew will generate artifacts in the `outputs/` directory:
1.  `research.md`: Detailed market research report.
2.  `strategy.md`: Comprehensive marketing strategy document.
3.  `generated_image.png`: (If ComfyUI is active) The concept image for the campaign.

## Troubleshooting

-   **ComfyUI Connection Error**: If you see "ComfyUI is NOT reachable", ensure your local ComfyUI instance is running and listening on port 8188.
-   **MCP Server Errors**: Check `log/log.txt` for detailed error messages regarding MCP tool loading.
