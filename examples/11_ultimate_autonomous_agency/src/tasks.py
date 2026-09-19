import os
from crewai import Task

class AgencyTasks:
    def __init__(self, example_root: str = ""):
        self.example_root = example_root

    def _get_path(self, relative_path: str) -> str:
        return os.path.join(self.example_root, relative_path)

    def analyze_requirements(self, agent, user_request):
        return Task(
            description=f"""
            Analyze the following user request and break it down into a detailed technical requirements document.
            Identify key features, constraints, and necessary technologies.
            
            IMPORTANT: Your Final Answer must be the content of the requirements document in Markdown format.
            Do NOT include conversational text like "Here is the document". Just the document content.
            
            User Request:
            {user_request}
            """,
            expected_output="A comprehensive markdown document outlining the project requirements, scope, and technical stack.",
            agent=agent,
            output_file=self._get_path("outputs/requirements.md")
        )

    def design_architecture(self, agent, requirements):
        return Task(
            description=f"""
            Based on the requirements, design the software architecture.
            Define the file structure, modules, classes, and key functions.
            Create a step-by-step implementation plan.
            
            IMPORTANT: Your Final Answer must be the content of the architecture document in Markdown format.
            Do NOT include conversational text.
            
            Requirements:
            {requirements}
            """,
            expected_output="A detailed architecture document and an implementation plan (JSON or Markdown list).",
            agent=agent,
            output_file=self._get_path("outputs/architecture.md")
        )

    def implement_code(self, agent, architecture):
        return Task(
            description=f"""
            Implement the software based on the architecture design.
            
            WORKING DIRECTORY: {self.example_root}
            
            IMPORTANT RULES:
            1. Write ALL generated application code to `outputs/src/`.
            2. Create `outputs/src/github_trending.py` containing the core implementation.
            3. Do NOT use `app.py`, `main.py`, or `setup.py`.
            4. `github_trending.py` MUST provide EXACTLY these functions:
               - `get_trending_repos(top_n: int = 3) -> list[dict]`
               - `save_repos_to_json(repos: list[dict], output_path: str) -> None`
               - `main() -> int` (returns 0 on success, 1 on failure)
            5. `main()` must write the output to the path returned by `_default_output_path()`.
            6. Do NOT change these signatures.
            6. Do NOT require API keys, tokens, or authentication.
            7. Use only Python standard library (no third-party deps).
            8. Do NOT create directories with the same name as python files (e.g. do not have `utils.py` and `utils/`).
            9. Include docstrings and type hints.
            
            Architecture:
            {architecture}
            """,
            expected_output="The complete source code written to files in outputs/src/. Return a summary of files created.",
            agent=agent
        )

    def run_tests(self, agent):
        return Task(
            description=f"""
            1. Write unit tests for the implemented code.
               - TARGET DIRECTORY: `outputs/TEST/`
               - FILENAME: `outputs/TEST/test_github_trending.py`
               - DO NOT create any subdirectories like `outputs/TEST/tests/`.
               - SOURCE IMPORT: Ensure you import the code from `outputs/src/`.
               - CAREFULLY CHECK function signatures in `outputs/src/github_trending.py` before writing tests.
                 For example, `save_repos_to_json` requires TWO arguments: (repos, output_path).
               - Do NOT assume any print statements in `main()`.
               - Your tests MUST call these EXACT functions (do not invent new names):
                 - `github_trending.get_trending_repos`
                 - `github_trending.save_repos_to_json`
                 - `github_trending.main`
               - Tests MUST be deterministic and must NOT depend on live network calls.
                 Use `monkeypatch` to replace `github_trending.get_trending_repos` or `github_trending.fetch_trending_html`.
            
            2. Run the tests using the 'Run Tests' tool.
               - ARGUMENT: `test_path="outputs/TEST/"`
            
            3. REPORTING:
               - If tests PASS: Return the word "PASSED" and a brief summary.
               - If tests FAIL: 
                 1. Analyze the failure.
                 2. Write a `outputs/bug_report.md` with details.
                 3. Return the word "FAILED" and a brief summary.
            
            FINAL ANSWER FORMAT:
            Just a text string starting with "PASSED" or "FAILED".
            Example: "FAILED. Syntax error in line 5."
            """,
            expected_output="A text string starting with PASSED or FAILED.",
            agent=agent,
            output_file=self._get_path("outputs/test_report.txt")
        )

    def fix_code(self, agent, test_report):
        return Task(
            description=f"""
            The tests have failed. Analyze the test report and fix the code.
            
            1. Read `outputs/bug_report.md` if it exists to get more details.
            2. Fix issues by editing files in `outputs/src/` and, if needed, `outputs/TEST/`.
            3. Ensure `outputs/TEST/` imports from `outputs/src/` using `../src` in sys.path.
            4. Enforce the API contract:
               - `outputs/src/github_trending.py` MUST expose `get_trending_repos`, `save_repos_to_json`, `main` at module level.
               - If tests are calling wrong function names, fix the tests (not the public API).
            5. Ensure the syntax is correct.
            
            Test Report:
            {test_report}
            """,
            expected_output="A summary of the fixes applied.",
            agent=agent
        )
