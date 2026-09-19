from crewai.tools import tool
import os
import subprocess
import sys
from typing import Optional

class FileTools:
    @staticmethod
    def _resolve_path(file_path: str) -> str:
        workspace_root = os.environ.get("AGENCY_WORKSPACE_ROOT")
        if workspace_root and not os.path.isabs(file_path):
            normalized_path = os.path.normpath(file_path)
            workspace_root = os.path.abspath(workspace_root)
            relative_parts = normalized_path.split(os.sep)
            workspace_prefix = os.environ.get("AGENCY_WORKSPACE_PREFIX")
            if workspace_prefix:
                prefix_parts = os.path.normpath(workspace_prefix).split(os.sep)
                if relative_parts[: len(prefix_parts)] == prefix_parts:
                    relative_parts = relative_parts[len(prefix_parts):]
            if not workspace_prefix:
                workspace_parts = os.path.normpath(workspace_root).split(os.sep)
                tail_parts = workspace_parts[-2:] if len(workspace_parts) >= 2 else workspace_parts
                if tail_parts and relative_parts[: len(tail_parts)] == tail_parts:
                    relative_parts = relative_parts[len(tail_parts):]
            if relative_parts:
                normalized_path = os.path.join(*relative_parts) if relative_parts else ""
            else:
                normalized_path = ""
            return os.path.abspath(os.path.join(workspace_root, normalized_path))
        return file_path

    @tool("Write File")
    def write_file(file_path: str, content: str):
        """
        Write content to a file. Overwrites if exists.
        Args:
            file_path: Absolute or relative path to the file.
            content: Text content to write.
        """
        try:
            resolved_path = FileTools._resolve_path(file_path)
            print(f"DEBUG: Write File called with path: {file_path}")
            print(f"DEBUG: Current CWD: {os.getcwd()}")
            
            # Ensure directory exists
            directory = os.path.dirname(resolved_path)
            if directory and not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
            
            with open(resolved_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            abs_path = os.path.abspath(resolved_path)
            print(f"DEBUG: Wrote to absolute path: {abs_path}")
            return f"Successfully wrote to {resolved_path}"
        except Exception as e:
            print(f"DEBUG: Error writing file: {e}")
            return f"Error writing file: {str(e)}"

    @tool("Read File")
    def read_file(file_path: str):
        """
        Read content from a file.
        Args:
            file_path: Path to the file.
        """
        resolved_path = FileTools._resolve_path(file_path)
        if not os.path.exists(resolved_path):
            return f"Error: File {resolved_path} not found."
        try:
            with open(resolved_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {str(e)}"

    @tool("List Files")
    def list_files(directory: str):
        """
        List files and directories in a given path.
        Args:
            directory: Path to the directory.
        """
        resolved_directory = FileTools._resolve_path(directory)
        if not os.path.exists(resolved_directory):
            return f"Error: Directory {resolved_directory} not found."
        try:
            return "\n".join(os.listdir(resolved_directory))
        except Exception as e:
            return f"Error listing files: {str(e)}"

    @tool("Create Directory")
    def create_directory(directory_path: str):
        """
        Create a new directory.
        Args:
            directory_path: Path to the directory to create.
        """
        try:
            resolved_directory = FileTools._resolve_path(directory_path)
            os.makedirs(resolved_directory, exist_ok=True)
            return f"Successfully created directory {resolved_directory}"
        except Exception as e:
            return f"Error creating directory: {str(e)}"


class ShellTools:
    @tool("Execute Shell Command")
    def execute_command(command: str, cwd: Optional[str] = None, timeout_seconds: int = 600):
        """
        Execute a shell command. Use this to run tests, install dependencies, etc.
        Args:
            command: The command to run (e.g., 'pytest', 'pip install requests').
            cwd: Optional working directory.
            timeout_seconds: Max seconds to allow the command to run.
        """
        try:
            # Security note: In a real environment, strictly sanitize inputs.
            # For this example, we assume trusted agents.
            
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            if result.returncode != 0:
                return f"Command failed with exit code {result.returncode}:\n{output}"
            return f"Command success:\n{output}"
        except Exception as e:
            return f"Error executing command: {str(e)}"

import json

class TestTools:
    @tool("Run Tests")
    def run_tests(test_dir: str = ".", cwd: Optional[str] = None):
        """
        Run tests using pytest and return structured JSON results.
        Args:
            test_dir: Directory containing tests (e.g., 'tests' or '.'). Defaults to current directory.
            cwd: Optional working directory for the test run.
        """
        try:
            command = f'"{sys.executable}" -m pytest {test_dir}'
            result = subprocess.run(
                command,
                cwd=cwd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            passed = result.returncode == 0
            
            # Analyze output for failed tests (simple parsing)
            failed_tests = []
            if not passed:
                # Look for lines like FAILED tests/test_foo.py::test_bar
                for line in result.stdout.splitlines():
                    if "FAILED" in line:
                        failed_tests.append(line.strip())
            
            summary = "Tests passed" if passed else "Tests failed"
            if result.returncode == 5:
                summary = "NO TESTS COLLECTED"
                passed = False
            
            return json.dumps({
                "passed": passed,
                "summary": summary,
                "failed_tests": failed_tests,
                "error_log": output[-2000:] # Truncate log
            })
        except Exception as e:
            return json.dumps({
                "passed": False,
                "summary": f"Error running tests: {str(e)}",
                "failed_tests": [],
                "error_log": str(e)
            })
