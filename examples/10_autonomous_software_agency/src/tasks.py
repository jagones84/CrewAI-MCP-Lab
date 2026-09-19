from crewai import Task
from pydantic import BaseModel, Field
from typing import List, Optional

# --- Pydantic Models for Structured Outputs ---

class FileSpec(BaseModel):
    path: str = Field(..., description="The relative path of the file")
    description: str = Field(..., description="What this file should contain")
    dependencies: List[str] = Field(default_factory=list, description="Libraries or other files this depends on")

class ProjectPlan(BaseModel):
    project_name: str = Field(..., description="Name of the project")
    architecture_overview: str = Field(..., description="High-level design summary")
    files: List[FileSpec] = Field(..., description="List of files to be created")
    test_strategy: str = Field(..., description="How the project will be tested")
    requirements_txt_content: str = Field(..., description="Content for requirements.txt")

class TestResult(BaseModel):
    passed: bool = Field(..., description="Whether all tests passed")
    summary: str = Field(..., description="Summary of test results")
    failed_tests: List[str] = Field(default_factory=list, description="Names of failed tests")
    error_log: str = Field(..., description="Relevant error logs")

# --- Tasks Class ---

class AgencyTasks:
    def __init__(self):
        pass

    def plan_project(self, agent, user_request: str):
        return Task(
            description=f"""
                Analyze the following user request and create a detailed technical plan.
                
                User Request:
                {user_request}
                
                Your plan must include:
                1. Project Name.
                2. Architectural Overview (patterns, libraries).
                3. A complete list of files to be created (src, tests, config, etc.).
                4. Content for requirements.txt.
                5. Testing strategy.
                
                YOU MUST RETURN A VALID JSON OBJECT (and nothing else) matching this structure:
                {{
                    "project_name": "string",
                    "architecture_overview": "string",
                    "files": [
                        {{
                            "path": "string (relative path)",
                            "description": "string",
                            "dependencies": ["string"]
                        }}
                    ],
                    "test_strategy": "string",
                    "requirements_txt_content": "string"
                }}
            """,
            expected_output="A valid JSON object containing the project plan.",
            agent=agent
        )

    def create_structure(self, agent, project_plan: ProjectPlan):
        return Task(
            description=f"""
                Based on the Project Plan, create the directory structure and empty files.
                
                Project Plan:
                {project_plan.model_dump_json()}
                
                INSTRUCTIONS:
                1. Use 'Create Directory' tool to create any necessary directories (e.g., 'tests', 'src').
                2. Use 'Write File' tool to create EACH file listed in the plan.
                3. For 'requirements.txt', use the content provided in the plan.
                4. For python files, you can write a placeholder comment.
                
                IMPORTANT: 
                - You MUST call tools SEPARATELY for each action.
                - Create directories FIRST.
                - Verify that you have created all files by using 'List Files' on the created directories.
                - If you fail to write a file, retry.
            """,
            expected_output="Confirmation that all directories and files have been initialized and verified.",
            agent=agent
        )

    def implement_code(self, agent, project_plan: ProjectPlan):
        return Task(
            description=f"""
                Implement the full code for the project based on the plan.
                
                Project Plan:
                {project_plan.model_dump_json()}
                
                INSTRUCTIONS:
                For each file in the plan:
                1. Write the actual working code using 'Write File'.
                2. Ensure all imports are correct and match `requirements.txt`.
                3. Write clean, commented code.
                4. Verify the file exists using 'Read File' (read first few lines) or 'List Files'.
                
                IMPORTANT: 
                - You MUST call 'Write File' SEPARATELY for EACH file.
                - Do NOT try to write multiple files in one tool call.
                - Do NOT assume success without checking.
            """,
            expected_output="Source code implemented and verified in all files.",
            agent=agent
        )

    def write_tests(self, agent, project_plan: ProjectPlan):
        return Task(
            description=f"""
                Write unit tests for the implemented code.
                
                Project Plan:
                {project_plan.model_dump_json()}
                
                INSTRUCTIONS:
                1. Create a `tests/` directory if not exists (handled by writing a file inside it).
                2. Write `test_*.py` files covering the main functionality using 'Write File'.
                3. Use `pytest` conventions.
                
                IMPORTANT:
                - Call 'Write File' for EACH test file.
                - Ensure you import the modules correctly from the src.
            """,
            expected_output="Test files created.",
            agent=agent
        )

    def run_tests(self, agent):
        return Task(
            description="""
                Run the tests using the 'Run Tests' tool.
                
                STEPS:
                1. Install dependencies: Run `pip install -r requirements.txt` using 'Execute Shell Command'.
                2. Run tests: Run 'Run Tests' tool. It will return a JSON with test results.
                3. Use the OUTPUT of 'Run Tests' tool as your final answer.
                
                IMPORTANT: 
                - You MUST use 'Run Tests' tool.
                - The tool output is ALREADY a JSON object. You just need to return it.
                - Do NOT change the results.
                
                YOU MUST RETURN A VALID JSON OBJECT (and nothing else) matching this structure:
                {
                    "passed": boolean,
                    "summary": "string",
                    "failed_tests": ["string"],
                    "error_log": "string"
                }
            """,
            expected_output="A valid JSON object containing the actual test execution result.",
            agent=agent
        )

    def fix_issues(self, agent, test_result: TestResult, project_plan: ProjectPlan):
        return Task(
            description=f"""
                The tests failed. Fix the code.
                
                Test Results:
                {test_result.model_dump_json()}
                
                1. Analyze the error logs.
                2. Modify the source code (or test code if the test is wrong) using 'Write File'.
                3. Return a summary of fixes.
            """,
            expected_output="Summary of fixes applied.",
            agent=agent
        )

    def write_documentation(self, agent):
        return Task(
            description="""
                Write a comprehensive `README.md` for the project.
                
                Include:
                1. Project Title & Description.
                2. Installation instructions.
                3. Usage examples.
                4. File structure overview.
                
                IMPORTANT: 
                - Use 'Write File' tool to create the README.md.
                - Do NOT use list of tool calls. Call the tool once with the full content.
            """,
            expected_output="README.md file created.",
            agent=agent
        )
