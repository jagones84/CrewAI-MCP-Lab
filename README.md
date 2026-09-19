# CrewAI MCP Lab

A collection of advanced CrewAI examples and experiments, featuring local/remote MCP integration.

## 📂 Projects

### 🖼️ [ComfyUI Image Generation](examples/04_comfyui_image_gen/README.md)
Minimal, self-contained CrewAI example that drives a ComfyUI MCP server end-to-end:
- **MCP server**: Reuses the same DGX Spark ComfyUI tunnel (`comfyui-dgspark`) used by the illustrated book writer.
- **Tool surface**: `generate_image`, `modify_image` (img2img), `upscale_image`, `remove_background`, `list_workflows` — all adapted from the canonical `~/.openclaw/.../comfyui-image-gen` skill on DGX.
- **Pipeline modes**: `simple` (one-shot generation) or `full` (generate → modify → upscale, with optional background removal).
- **Bundled mock**: Ships a `comfyui-mock` MCP fallback so the example is runnable on any machine, no GPU required.
- **LLM**: OpenRouter by default (swap to Ollama, OpenAI, or llama.cpp via `config/preferences.yaml`).
- **Output**: One PNG per pipeline step in `outputs/` (`generated.png`, `modified.png`, `upscaled.png`, optionally `no_bg.png`).

### 📖 [Illustrated Book Writer](examples/05_illustrated_book_writer/README.md)
A fully autonomous agent crew that writes, edits, and illustrates complete novels using:
- **CrewAI**: For agent orchestration (Writer, Editor, Illustrator, Architect).
- **LLM Support**: Supports **OpenRouter** (GPT-4o, Claude 3, etc.), **Llama.cpp**, and **Ollama**.
- **ComfyUI**: For character consistent image generation.
- **RAG**: For narrative continuity.

### 🎥 [YouTube Researcher](examples/06_youtube_researcher/README.md)
A CrewAI workflow that researches, transcribes, and summarizes YouTube videos using:
- **DuckDuckGo MCP**: For finding relevant videos.
- **yt-whisper MCP**: For transcribing video content.
- **LLM Support**: Flexible LLM integration via **OpenRouter** or local providers.
- **LLM**: For summarizing the transcripts.

### 🎬 [Movie Analyst](examples/07_movie_analyst/README.md)
An agent crew that analyzes movies for streaming availability and critical reception:
- **JustWatch MCP**: Locates streaming services in Italy.
- **Brave Search MCP**: Aggregates reviews and ratings.
- **Reporting**: Generates a markdown report with findings.

### 📈 [Financial Analyst](examples/08_financial_analyst/README.md)
A multi-agent crew that performs deep financial analysis using real-time market data:
- **YFinance MCP**: Fetches stock prices, company info, and technical indicators (RSI, SMA).
- **Multi-Agent Analysis**: Combines data collection, technical analysis, and journalistic reporting.
- **Automated Reporting**: Generates a professional Markdown investment report in the `output/` folder.

### 📢 [Marketing Strategy](examples/09_marketing_strategy/README.md)
A multi-modal crew for creating comprehensive marketing campaigns:
- **DuckDuckGo MCP**: Conducts real-time market and competitor research.
- **LLM Strategy**: Develops USPs, taglines, and campaign concepts.
- **ComfyUI MCP**: Generates visual concept art for the campaign.

### 🏢 [Autonomous Software Agency](examples/10_autonomous_software_agency/README.md)
A complete, autonomous software agency built with **CrewAI Flows**:
- **Flow lifecycle**: Plan → Code → Test → Fix → Document.
- **Self-healing**: failed tests route back to the Developer agent (up to 3 retries).
- **Project isolation**: all work happens in `outputs/workspace/`.
- **Structured outputs**: Pydantic schemas for Plans and Test Results.
- **SQLite MCP** (optional): logs project metadata to a local "corporate memory".

### 🌐 [Ultimate Autonomous Agency](examples/11_ultimate_autonomous_agency/README.md)
The most complete CrewAI demonstration: Flows + hierarchical processes + custom MCP servers + self-healing loops:
- **Elite architecture**: `Process.hierarchical` with a Manager agent.
- **Persistent Memory MCP**: custom local SQLite MCP server for cross-step project context.
- **Self-healing**: robust Code → Test → Fix loop until tests pass.
- **Structured outputs**: strict Pydantic typing between agents.

## 🛠️ Comprehensive Setup Guide

This project uses a **Dual-Layer Architecture**:
1.  **Root Venv**: Runs the CrewAI Agents and orchestration logic.
2.  **MCP Venvs**: Each MCP server (e.g., ComfyUI) runs in its own isolated environment to avoid dependency conflicts.

### 1. Root Environment Setup
(Run from the repository root)

```powershell
# Create Root Virtual Environment
python -m venv venv

# Activate
.\venv\Scripts\activate

# Install Core Dependencies
pip install -r requirements.txt
```

### 2. MCP Servers Setup
Run these commands to prepare the isolated environments for each tool:

```powershell
# 1. ComfyUI (Local)
cd mcp_servers/comfyui
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ../..

# 2. ComfyUI (DGX Spark / Remote)
cd mcp_servers/comfyui-dgspark
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ../..

# 3. YouTube Whisper
cd mcp_servers/yt-whisper
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ../..

# 4. Simple Datetime (Node.js)
cd mcp_servers/simple-datetime-server
npm install
cd ../..

# 5. YFinance MCP
cd mcp_servers/yfinance_mcp
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
deactivate
cd ../..
```

### 3. Configuration

#### A. Global MCP Configuration (`crewai_mcp.json`)
This file tells CrewAI where to find your tools.
1.  Copy `crewai_mcp.template.json` to `crewai_mcp.json`.
2.  Ensure paths point to **local folders** (relative paths are supported and recommended).
    *   Example for Local ComfyUI: `"command": "mcp_servers/comfyui/.venv/Scripts/python.exe"`
    *   Example for Remote DGX: `"command": "mcp_servers/comfyui-dgspark/.venv/Scripts/python.exe"`

#### B. Application Configuration (`config.yaml`)
1.  Navigate to `examples/05_illustrated_book_writer/config/`.
2.  Copy `config.template.yaml` to `config.yaml`.
3.  Edit `config.yaml` to select your profiles:
    ```yaml
    infrastructure:
      # LLM Provider: Choose "openrouter", "llama_cp", "llama_cp_local", or "ollama"
      llm_selected: "openrouter" 
      
      # Image Provider: Choose "local_standard" or "remote_dgspark"
      image_selected: "remote_dgspark" 
    ```

#### C. LLM Support & OpenRouter
This project is optimized for **OpenRouter**, allowing you to use state-of-the-art models (GPT-4o, Claude 3.5 Sonnet, etc.) with minimal setup.
- Ensure your `OPENAI_API_KEY` in `.env` is set to your OpenRouter key.
- The system automatically handles the routing to OpenRouter endpoints when configured.

## 🚀 Running the Application

**CRITICAL**: Always run from the **Project Root** using the **Root Venv**.

```powershell
# 1. Activate Root Venv
.\venv\Scripts\activate

# 2. Run the Illustrated Book Writer
cd examples/05_illustrated_book_writer
python src/main.py

# 3. Run the Financial Analyst
cd examples/08_financial_analyst
python src/main.py
```

## ⚡ Remote GPU (DGX Spark) Integration

The `comfyui-dgspark` MCP server handles SSH tunneling automatically.

1.  **Prerequisite**: Ensure you have SSH key access to your remote server.
2.  **Configuration**: In `config.yaml`, select `image_selected: "remote_dgspark"`.
3.  **Operation**: The system will:
    *   Start the local MCP wrapper.
    *   Establish an SSH tunnel (e.g., Local 8189 -> Remote 8188).
    *   Send requests to the remote ComfyUI instance.
    *   Download generated images back to your local machine.

## 🧪 Testing

To verify the architecture without running the full book generation:

**DGX Spark / Remote Test:**
```powershell
python mcp_servers/comfyui-dgspark/TEST/test_crewai_agent_dgspark.py
```

**Local ComfyUI Test:**
```powershell
python mcp_servers/comfyui/TEST/test_crewai_agent.py
```
