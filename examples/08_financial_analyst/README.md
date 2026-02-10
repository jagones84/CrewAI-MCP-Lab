# 08 Financial Analyst Crew

This example demonstrates a multi-agent crew that performs financial analysis using a custom **YFinance MCP Server**.

## Overview
The crew consists of three agents:
1.  **Data Collector**: Uses the `yfinance` MCP tool to fetch real-time stock prices, company info, and historical data.
2.  **Financial Analyst**: Analyzes the raw data to identify trends, valuation metrics, and risks.
3.  **Financial Journalist**: Compiles the analysis into a professional Markdown report.

## Prerequisites
- Python 3.10+
- [Ollama](https://ollama.com/) running with `llama3` (or configured model).

## Configuration
1.  Copy `.env.example` to `.env` (if needed, though this example uses no API keys by default).
2.  Edit `config/preferences.yaml` to change the stock tickers or LLM settings.

## Installation
```bash
pip install -r requirements.txt
```

## Usage
Run the main script:
```bash
python src/main.py
```

## Architecture
- **MCP Server**: Located in `mcp_servers/yfinance_mcp`. It provides tools like `get_stock_price`, `get_stock_history`.
- **MCP Loader**: A utility in `src/utils` loads the MCP server using `config/mcp_config.json`.
