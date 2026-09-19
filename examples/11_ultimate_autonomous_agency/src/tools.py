import subprocess
import os
import json
import sqlite3
import sys
from crewai.tools import tool

# Base path for the example
EXAMPLE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(EXAMPLE_ROOT, "outputs", "memory.db")


def _resolve_example_path(file_path: str) -> str:
    return os.path.abspath(os.path.join(EXAMPLE_ROOT, file_path))


def run_pytest_command(test_path: str = "TEST/") -> str:
    """Run pytest using the current Python interpreter for Windows-safe execution."""
    try:
        full_test_path = _resolve_example_path(test_path)

        if not os.path.exists(full_test_path):
            return f"Error: Test path '{full_test_path}' does not exist."

        result = subprocess.run(
            [sys.executable, "-m", "pytest", full_test_path],
            cwd=EXAMPLE_ROOT,
            capture_output=True,
            text=True
        )

        output = (result.stdout or "") + "\n" + (result.stderr or "")
        passed = result.returncode == 0

        summary_lines = [
            line for line in output.split('\n')
            if "passed" in line.lower() or "failed" in line.lower() or "error" in line.lower()
        ]
        summary = "\n".join(summary_lines[-3:])

        return json.dumps({
            "passed": passed,
            "exit_code": result.returncode,
            "summary": summary,
            "full_output": output[:2000]
        }, indent=2)
    except Exception as e:
        return f"Error running tests: {str(e)}"

class PersistentMemoryTools:
    @tool("Save Memory")
    def save_memory(key: str, value: str, category: str = "general") -> str:
        """
        Save a piece of information to the persistent memory.
        Useful for storing architectural decisions, bug reports, or project status.
        """
        try:
            os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
            conn = sqlite3.connect(DB_PATH)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    category TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute(
                "INSERT OR REPLACE INTO memories (key, value, category) VALUES (?, ?, ?)",
                (key, value, category)
            )
            conn.commit()
            conn.close()
            return f"Successfully saved memory: {key}"
        except Exception as e:
            return f"Error saving memory: {str(e)}"

    @tool("Read Memory")
    def read_memory(key: str) -> str:
        """Retrieve a specific memory by its key."""
        try:
            if not os.path.exists(DB_PATH):
                return "Memory database does not exist yet."
            conn = sqlite3.connect(DB_PATH)
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT value, category FROM memories WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            if row:
                return f"[{row['category']}] {row['value']}"
            return "Memory not found."
        except Exception as e:
            return f"Error reading memory: {str(e)}"

class TestTools:
    @tool("Run Tests")
    def run_tests(test_path: str = "TEST/") -> str:
        """
        Runs pytest on the specified directory or file.
        Returns a structured summary of the results.
        """
        return run_pytest_command(test_path)

class FileTools:
    @tool("Write Code File")
    def write_file(file_path: str, content: str) -> str:
        """
        Writes code to a file. 
        Args:
            file_path: The relative path to the file (e.g., 'src/my_module.py').
            content: The code content.
        """
        try:
            full_path = _resolve_example_path(file_path)

            # Safety check: Prevent overwriting system files outside the example
            if os.path.commonpath([EXAMPLE_ROOT, full_path]) != EXAMPLE_ROOT:
                return "Error: Cannot write outside example directory."
            
            # PROTECT CRITICAL FILES
            protected_files = ["src/main.py", "src/agents.py", "src/tasks.py", "src/tools.py", "src/utils.py"]
            # Check relative path
            rel_path = os.path.relpath(full_path, EXAMPLE_ROOT).replace("\\", "/")
            if rel_path in protected_files:
                return f"Error: Cannot overwrite protected system file '{rel_path}'."

            allowed_prefixes = ("outputs/src/", "outputs/TEST/")
            allowed_files = {
                "outputs/requirements.md",
                "outputs/architecture.md",
                "outputs/test_report.txt",
                "outputs/bug_report.md",
            }
            if not (rel_path.startswith(allowed_prefixes) or rel_path in allowed_files):
                return f"Error: Writes are only allowed under outputs/src/ or outputs/TEST/. Got '{rel_path}'."

            forbidden_files = {"outputs/src/app.py", "outputs/src/main.py", "outputs/src/setup.py"}
            if rel_path in forbidden_files:
                return f"Error: Do not write '{rel_path}'. Use a descriptive module name."

            content_stripped = content.strip()
            if content_stripped.startswith("```"):
                lines = content_stripped.split("\n")
                if lines and lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                content = "\n".join(lines)

            rel_path_normalized = rel_path.lower()
            if rel_path_normalized.endswith(".py"):
                lines = content.splitlines()
                while lines and lines[0].strip().startswith(("Thought:", "Action:", "Action Input:", "Observation:", "Final Answer:")):
                    lines = lines[1:]
                content = "\n".join(lines).lstrip()

            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {file_path} (absolute: {full_path})"
        except Exception as e:
            return f"Error writing file: {str(e)}"

    @tool("Read File")
    def read_file(file_path: str) -> str:
        """Reads a file's content."""
        try:
            full_path = _resolve_example_path(file_path)
            if os.path.commonpath([EXAMPLE_ROOT, full_path]) != EXAMPLE_ROOT:
                return f"Error: File {file_path} is outside the example directory."
            if not os.path.exists(full_path):
                return f"Error: File {full_path} not found."
            with open(full_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"
