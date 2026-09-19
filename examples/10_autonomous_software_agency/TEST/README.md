# Testing the Autonomous Software Agency

This directory contains unit tests for the agency's components.

## Running Tests

To run all tests:
```bash
python -m unittest discover TEST
```

To run a specific test file:
```bash
python TEST/test_tools.py
python TEST/test_sqlite_mcp.py
```

## Test Files

- `test_tools.py`: Validates the `FileTools` used by agents to read/write files.
- `test_sqlite_mcp.py`: Validates the connection to the SQLite MCP server.
