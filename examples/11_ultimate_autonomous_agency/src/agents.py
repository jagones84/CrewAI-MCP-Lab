from crewai import Agent
from .utils import get_llm
from .tools import FileTools, TestTools, PersistentMemoryTools

class AgencyAgents:
    def __init__(self):
        self.llm = get_llm("llm")
        self.manager_llm = get_llm("manager_llm")
        
        # Common tools for all agents to access memory
        self.memory_tools = [PersistentMemoryTools.save_memory, PersistentMemoryTools.read_memory]

    def chief_architect(self):
        return Agent(
            role='Chief Architect',
            goal='Design robust, scalable, and maintainable software architectures.',
            backstory="""You are a veteran software architect with 20 years of experience. 
            You design systems that are modular, easy to test, and use modern best practices. 
            You prefer clean architecture and strict separation of concerns.""",
            llm=self.manager_llm,
            verbose=True,
            allow_delegation=True,
            memory=True,
            tools=self.memory_tools + [FileTools.read_file]
        )

    def product_manager(self):
        return Agent(
            role='Product Manager',
            goal='Define clear, actionable, and comprehensive project requirements.',
            backstory="""You are an expert Product Manager. You take vague requests and turn them into 
            detailed, professional requirements documents. You ensure every requirement is testable.""",
            llm=self.llm,
            verbose=True,
            memory=True,
            tools=self.memory_tools
        )

    def senior_developer(self):
        return Agent(
            role='Senior Developer',
            goal='Implement clean, efficient, and error-free code based on specifications.',
            backstory="""You are a 10x Python Developer. 
            - You write PEP8 compliant code.
            - You ALWAYS include docstrings.
            - You handle errors gracefully with try/except blocks.
            - You write modular code, never one giant script.
            - You double-check your imports to ensure they work relative to the execution point.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            tools=[FileTools.write_file, FileTools.read_file] + self.memory_tools,
            memory=True
        )

    def qa_engineer(self):
        return Agent(
            role='QA Engineer',
            goal='Ensure code quality through rigorous testing and bug reporting.',
            backstory="""You are a Senior QA Engineer expert in Pytest.
            - You write comprehensive test suites.
            - You NEVER write syntax errors.
            - You NEVER use lambdas for test cases.
            - You always verify that the code under test is importable.
            - You provide detailed, actionable bug reports.""",
            llm=self.llm,
            verbose=True,
            allow_delegation=False,
            tools=[TestTools.run_tests, FileTools.read_file, FileTools.write_file] + self.memory_tools,
            memory=True
        )
