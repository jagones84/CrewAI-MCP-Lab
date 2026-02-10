# Example 06: YouTube Researcher

This example demonstrates how to use CrewAI with MCP tools to research, transcribe, and summarize YouTube videos.

## Features
- **Web Search**: Uses DuckDuckGo MCP to find relevant videos.
- **Video Transcription**: Uses `yt-whisper` MCP to transcribe videos.
- **Summarization**: Summarizes the content using an LLM.

## Setup

### 1. Prerequisites
- Python 3.10+
- [Optional] CUDA-capable GPU for faster transcription.

### 2. Install Dependencies
Run this in the project root:
```bash
pip install -r requirements.txt
```

### 3. Configure yt-whisper (Important!)
The transcription server requires its own virtual environment. The dependencies for CUDA-enabled transcription are included in the `requirements.txt`.

```powershell
cd mcp_servers/yt-whisper
python -m venv .venv
.\.venv\Scripts\activate

# Install all dependencies (including CUDA-enabled PyTorch)
pip install -r requirements.txt

deactivate
```

### 4. Run the Example
Return to the project root and run:
```powershell
cd examples/06_youtube_researcher
python src/main.py
```

## Outputs
Transcriptions and logs will be saved in `examples/06_youtube_researcher/outputs/`.
