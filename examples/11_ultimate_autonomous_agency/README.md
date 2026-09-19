# Example 11: Ultimate Autonomous Agency

## Overview
The **Ultimate Autonomous Agency** is the most complete demonstration of CrewAI's capabilities as of 2026. It integrates **CrewAI Flows**, **Hierarchical Processes**, **Custom MCP Servers**, and **Self-Healing Loops** into a single cohesive system.

## Features
- **Elite Architecture**: Uses `Process.hierarchical` with a Manager Agent for high-level orchestration.
- **CrewAI Flow**: Manages the state and transitions between Planning, Execution, and Validation phases.
- **Persistent Memory MCP**: A custom, local SQLite-based MCP server (`mcp_servers/persistent_memory`) that allows agents to store and retrieve project context (Decisions, Bugs, Status) across execution steps.
- **Self-Healing**: A robust `Code -> Test -> Fix` loop that retries until tests pass.
- **Structured Outputs**: Uses Pydantic models for strict type enforcement between agents.

## Architecture

### Flow
1.  **Requirement Analysis**: Product Manager breaks down the user request.
2.  **Architecture Planning**: Chief Architect designs the solution.
3.  **Development**: Senior Developer implements the code.
4.  **Quality Assurance**: QA Engineer writes and runs tests using `pytest`.
5.  **Refinement Loop**: If tests fail, the flow routes back to the Developer with specific error logs.

### MCP Server: Persistent Memory
A custom MCP server providing tools:
- `save_memory(key, value, category)`
- `read_memory(key)`
- `search_memory(query)`
This allows the "Corporate Brain" to persist beyond the immediate context window.

## Prerequisites
- Python 3.10+
- [Optional] Ollama for local LLMs (Mistral, Llama3)
- [Optional] OpenAI/OpenRouter API Key

## Installation
```bash
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys or preferences
```

## Usage
```bash
python src/main.py
```
