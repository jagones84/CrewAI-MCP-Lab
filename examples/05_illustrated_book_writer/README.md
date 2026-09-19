# Illustrated Book Writer

An advanced AI agent system that writes, edits, and illustrates full novels using CrewAI.

## 🚀 Overview

This project uses a crew of AI agents (Architect, Writer, Editor, Illustrator) to generate coherent, illustrated books. It supports:
- **Local LLMs**: Integration with Llama.cpp, Ollama, or LM Studio.
- **Remote Image Generation**: ComfyUI integration (local or remote via SSH).
- **RAG Memory**: Uses ChromaDB to maintain narrative consistency.
- **PDF Publishing**: Automatically compiles the story and images into a formatted PDF.

## 🛠️ Infrastructure Setup

This example is designed to run on a local PC while offloading heavy computation to a DGX Spark host or another supported LLM provider.

### DGX Spark Default Setup

Example 05 now defaults to a DGX Spark-hosted `llama.cpp` model exposed through an SSH tunnel.
The remote DGX server must already be running the expected model before you start the local app.

1. Run `scripts\start_tunnels.bat`
2. Run `python scripts\test_dgx_llm_tunnel.py`
3. Run `python src/main.py`

The default LLM profile is `qwen_abliterated_dgx`, currently mapped to the live DGX model alias `qwen-3.6-35b-a3b-claude47-opus-abliterated`.

**On Remote Machine (Linux):**
Run `scripts/start_llama_server.sh` to start the remote `llama.cpp` server if it is not already running.

### Other LLM Options

The DGX path is the default, but the example still supports these providers:

- `llama_cp_local`: local auto-managed `llama.cpp`
- `ollama`: local auto-managed Ollama
- `openrouter`: cloud OpenRouter
- `llama_cp`: generic external OpenAI-compatible `llama.cpp`

### Provider Notes

#### OpenRouter Setup
If you prefer to use a cloud model through OpenRouter:

1. Get an API key from [OpenRouter.ai](https://openrouter.ai/).
2. Set `llm_selected: "openrouter"` in `config/config.yaml`.
3. Update the `openrouter` profile with your preferred model and API key source.

#### Local Llama.cpp Setup
If you prefer to run the LLM locally on Windows with full automation:

1. Download the latest release from the [Official Llama.cpp Repository](https://github.com/ggerganov/llama.cpp/releases).
2. Download one or more GGUF models and store them in your local models directory.
3. Set `llm_selected: "llama_cp_local"` and update the `llama_cp_local` profile paths in `config/config.yaml`.

#### Local Ollama Setup
If you prefer to run the LLM locally with Ollama:

1. Install Ollama from the [Official Ollama Website](https://ollama.com/download).
2. Pull the model you want to use, for example `ollama pull llama3`.
3. Set `llm_selected: "ollama"` and update the `ollama` profile in `config/config.yaml`.

### Configuration
Edit `config/config.yaml`. You can copy `config/config.template.yaml` to `config/config.yaml` to get started.

```yaml
infrastructure:
  llm_selected: "qwen_abliterated_dgx" # Options: "qwen_abliterated_dgx", "llama_cp_local", "ollama", "openrouter", etc.
  image_selected: "remote_dgspark"

  llm_profiles:
    qwen_abliterated_dgx:
      model: "qwen-3.6-35b-a3b-claude47-opus-abliterated"
      base_url: "http://localhost:11003/v1"
    llama_cp_tunnel:
      base_url: "http://localhost:11003/v1" # Example tunnelled port
    llama_cp:
       # For Generic Local Servers (e.g. LM Studio, LocalAI)
       base_url: "http://localhost:1234/v1"
```

### Port Mapping Examples

*Note: These are example mappings used in the provided scripts.*

| Service | Local Port | Remote Port | Description |
| :--- | :--- | :--- | :--- |
| ComfyUI | 11002 | 8188 | Default DGX image generation path |
| DGX `llama.cpp` | 11003 | 8092 | Default example 05 LLM path |
| Ollama | 11435 | 11434 | Optional fallback API tunnel |

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd examples/05_illustrated_book_writer
    ```

2.  **Create Virtual Environment**:
    ```bash
    python -m venv venv
    .\venv\Scripts\activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

## 🏃 Usage

Run the main application:
```bash
python src/main.py
```

The output (PDF, images, logs) will be saved in the `outputs/` directory under your book's title.

## 📁 Directory Structure

*   `src/`: Source code for agents, tasks, and flow logic.
*   `config/`: Configuration files (`config.yaml`, `settings.py`).
*   `scripts/`: Helper scripts for infrastructure (SSH tunnels, server startup).
*   `outputs/`: Generated books, logs, and assets.

## 📝 Logging

Logs are written to `outputs/logs/session.log`. Check this file for detailed execution traces and error messages.
