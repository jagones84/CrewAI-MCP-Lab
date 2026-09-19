from mcp.server.fastmcp import FastMCP
import sqlite3
import json
import os
from typing import List, Dict, Any, Optional

mcp = FastMCP("SQLite")

def _get_connection(db_path: str) -> sqlite3.Connection:
    db_dir = os.path.dirname(db_path)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

@mcp.tool()
def query_db(db_path: str, query: str) -> str:
    """
    Execute a SELECT or PRAGMA query on the SQLite database.
    Args:
        db_path: Path to the SQLite database file.
        query: The SQL query to execute.
    Returns:
        JSON string containing the query results.
    """
    if not query.strip().upper().startswith("SELECT") and not query.strip().upper().startswith("PRAGMA"):
        return json.dumps({"error": "Only SELECT or PRAGMA queries are allowed in query_db. Use execute_db for modifications."})
    
    try:
        with _get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            return json.dumps([dict(row) for row in rows], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def execute_db(db_path: str, query: str) -> str:
    """
    Execute an INSERT, UPDATE, DELETE, or CREATE query on the SQLite database.
    Args:
        db_path: Path to the SQLite database file.
        query: The SQL query to execute.
    Returns:
        JSON string containing the operation result (e.g., number of rows affected).
    """
    try:
        with _get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(query)
            conn.commit()
            return json.dumps({"status": "success", "rows_affected": cursor.rowcount})
    except Exception as e:
        return json.dumps({"error": str(e)})

@mcp.tool()
def inspect_schema(db_path: str) -> str:
    """
    Inspect the schema of the SQLite database.
    Args:
        db_path: Path to the SQLite database file.
    Returns:
        JSON string containing the database schema (tables and columns).
    """
    try:
        with _get_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            schema = {}
            for table in tables:
                table_name = table['name']
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                schema[table_name] = [dict(col) for col in columns]
            return json.dumps(schema, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    mcp.run()
