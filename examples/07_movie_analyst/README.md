# Example 07: Movie Analyst

This example demonstrates how to use CrewAI with MCP tools to analyze a movie, finding its streaming availability in Italy (via JustWatch) and summarizing critical reviews (via Brave Search).

## Features
- **Streaming Availability**: Uses `justwatch` MCP tool to find where to stream the movie in Italy.
- **Review Analysis**: Uses `brave-search` MCP tool to find and summarize reviews.
- **Reporting**: Compiles the findings into a markdown report.

## Setup

### 1. Prerequisites
- Python 3.10+
- `crewai` installed
- `uvx` (from `uv`) installed for running `mcp-justwatch`.
- `brave-search` MCP server configured with an API key.

### 2. Configuration
Ensure your `crewai_mcp.json` has `justwatch` and `brave-search` enabled.
The `brave-search` server requires a `BRAVE_API_KEY` in the environment variables or the config file.

### 3. Run the Example
Return to the project root and run:
```powershell
cd examples/07_movie_analyst
python src/main.py
```

## Outputs
The final report will be saved in `examples/07_movie_analyst/outputs/`.
