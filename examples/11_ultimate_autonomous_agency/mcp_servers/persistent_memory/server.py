from fastmcp import FastMCP
import sqlite3
import os
from typing import List, Optional
from pydantic import BaseModel

# Initialize FastMCP
mcp = FastMCP("PersistentMemory")

# Database Setup
EXAMPLE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(EXAMPLE_ROOT, "outputs", "memory.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS memories (
            key TEXT PRIMARY KEY,
            value TEXT,
            category TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

@mcp.tool()
def save_memory(key: str, value: str, category: str = "general") -> str:
    """
    Save a piece of information to the persistent memory.
    Useful for storing architectural decisions, bug reports, or project status.
    """
    try:
        conn = get_db()
        conn.execute(
            "INSERT OR REPLACE INTO memories (key, value, category) VALUES (?, ?, ?)",
            (key, value, category)
        )
        conn.commit()
        conn.close()
        return f"Successfully saved memory: {key}"
    except Exception as e:
        return f"Error saving memory: {str(e)}"

@mcp.tool()
def read_memory(key: str) -> str:
    """
    Retrieve a specific memory by its key.
    """
    try:
        conn = get_db()
        cursor = conn.execute("SELECT value, category FROM memories WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return f"[{row['category']}] {row['value']}"
        return "Memory not found."
    except Exception as e:
        return f"Error reading memory: {str(e)}"

@mcp.tool()
def search_memories(query: str) -> str:
    """
    Search for memories containing the query string in their key or value.
    """
    try:
        conn = get_db()
        cursor = conn.execute(
            "SELECT key, value, category FROM memories WHERE key LIKE ? OR value LIKE ?",
            (f"%{query}%", f"%{query}%")
        )
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "No matching memories found."
        
        results = []
        for row in rows:
            results.append(f"- {row['key']} ({row['category']}): {row['value']}")
        return "\n".join(results)
    except Exception as e:
        return f"Error searching memories: {str(e)}"

@mcp.tool()
def list_all_memories() -> str:
    """
    List all stored memories.
    """
    try:
        conn = get_db()
        cursor = conn.execute("SELECT key, category FROM memories")
        rows = cursor.fetchall()
        conn.close()
        
        if not rows:
            return "Memory is empty."
        
        results = []
        for row in rows:
            results.append(f"- {row['key']} ({row['category']})")
        return "\n".join(results)
    except Exception as e:
        return f"Error listing memories: {str(e)}"

if __name__ == "__main__":
    mcp.run()
