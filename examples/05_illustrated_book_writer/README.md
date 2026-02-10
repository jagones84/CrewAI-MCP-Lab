# Illustrated Book Writer

An advanced AI agent system that writes, edits, and illustrates full novels using CrewAI.

## 🚀 Overview

This project uses a crew of AI agents (Architect, Writer, Editor, Illustrator) to generate coherent, illustrated books. It supports:
- **Local LLMs**: Integration with Llama.cpp, Ollama, or LM Studio.
- **Remote Image Generation**: ComfyUI integration (local or remote via SSH).
- **RAG Memory**: Uses ChromaDB to maintain narrative consistency.
- **PDF Publishing**: Automatically compiles the story and images into a formatted PDF.

## 🛠️ Infrastructure Setup

This project is designed to run on a local PC while offloading heavy computation (LLM & Image Generation) to a remote GPU server.

### 1. Connection Scripts
Use the scripts in the `scripts/` directory as templates to establish the necessary tunnels and servers.

**On Local PC (Windows):**
Run `scripts\start_tunnels.bat` (after editing your remote IP/username) to open SSH tunnels to your remote machine.

**On Remote Machine (Linux):**
Run `scripts/start_llama_server.sh` to start the Llama.cpp server (optimized for high-end GPUs).

### 2. OpenRouter Setup (Recommended for Cloud)
If you prefer to use high-quality cloud models (like GPT-4, Claude 3, or Llama 3 70B) via OpenRouter:

1.  **Get API Key**: Sign up at [OpenRouter.ai](https://openrouter.ai/) and get an API key.
2.  **Configure `config.yaml`**:
    *   Set `llm_selected: "openrouter"`.
    *   Update the `openrouter` profile:
        ```yaml
        openrouter:
          model: "openai/gpt-4o-mini" # Or "anthropic/claude-3-opus", etc.
          base_url: "https://openrouter.ai/api/v1"
          # api_key: "sk-or-..." # Set in environment or config
        ```

### 3. Local Llama.cpp Setup (Optional)
If you prefer to run the LLM locally on your Windows machine with full automation:

1.  **Download Llama.cpp**:
    *   Get the latest release (e.g., `llama-bxxxx-bin-win-avx2-x64.zip`) from the [Official Llama.cpp Repository](https://github.com/ggerganov/llama.cpp/releases).
    *   Extract it to a folder (e.g., `F:\PROGRAMS\llama_cp`).

2.  **Download Models**:
    *   Download GGUF models (e.g., from HuggingFace).
    *   Place them in a dedicated folder (e.g., `F:\PROGRAMS\llama_cp\MODELS`).

3.  **Configure `config.yaml`**:
    *   Set `llm_selected: "llama_cp_local"`.
    *   Update the `llama_cp_local` profile with your paths:
        ```yaml
        llama_cp_local:
          model: "Cydonia-24B-v4j-Q4_K_M.gguf"
          executable_path: "F:\\PROGRAMS\\llama_cp\\llama-server.exe"
          models_dir: "F:\\PROGRAMS\\llama_cp\\MODELS"
        ```
    *   The application will now **automatically** start/stop the server and load the correct model when you run `src/main.py`.

### 4. Local Ollama Setup (Optional)
If you prefer to run the LLM locally using Ollama with full automation:

1.  **Install Ollama**:
    *   Download and install from the [Official Ollama Website](https://ollama.com/download).
    *   Ensure `ollama` is in your system PATH or note the installation path (usually `C:\Users\%USERNAME%\AppData\Local\Programs\Ollama\ollama.exe`).

2.  **Pull Models**:
    *   Run `ollama pull llama3` (or any other model) in your terminal.
    *   Or let the application pull it automatically (first run might be slower).

3.  **Configure `config.yaml`**:
    *   Set `llm_selected: "ollama"`.
    *   Update the `ollama` profile:
        ```yaml
        ollama:
          model: "llama3"
          executable_path: "C:\\Users\\%USERNAME%\\AppData\\Local\\Programs\\Ollama\\ollama.exe"
        ```
    *   The application will **automatically** start Ollama (if not running), kill conflicting Llama.cpp servers, and ensure the model is loaded.

### 5. Configuration
Edit `config/config.yaml`. You can copy `config/config.template.yaml` to `config/config.yaml` to get started.

```yaml
infrastructure:
  llm_selected: "ollama" # Options: "llama_cp_local", "ollama", "openrouter", etc.
  image_selected: "remote_dgspark"

  llm_profiles:
    llama_cp_tunnel:
      base_url: "http://localhost:11003/v1" # Example tunnelled port
    llama_cp:
       # For Generic Local Servers (e.g. LM Studio, LocalAI)
       base_url: "http://localhost:1234/v1"
```

### 6. Port Mapping Examples

*Note: These are example mappings used in the provided scripts.*

| Service | Local Port | Remote Port | Description |
| :--- | :--- | :--- | :--- |
| ComfyUI | 11002 | 8188 | Image Generation Backend |
| Llama CP | 11003 | 11005 | Custom Llama Server |
| Ollama | 11435 | 11434 | Ollama API |

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
