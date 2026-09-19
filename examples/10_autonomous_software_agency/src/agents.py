import os

from crewai import Agent, LLM

from tools import FileTools, ShellTools, TestTools
from utils.llm_utils import unload_vram
from utils.mcp_loader import MCPLoader


STALE_OPENROUTER_MODELS = {
    "google/gemini-2.0-flash-001": "google/gemini-2.5-flash-lite",
}

class AgencyAgents:
    def __init__(self, config):
        self.config = config
        self.llm_config = config.get('llm', {})
        
        # Unload VRAM if using Ollama
        if self.llm_config.get("provider") == "ollama":
            ollama_cfg = self.llm_config.get("ollama", {})
            base_url = (
                ollama_cfg.get("base_url")
                or self.llm_config.get("base_url")
                or os.environ.get("OLLAMA_BASE_URL")
                or "http://localhost:11434"
            )
            base_url = base_url.rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            unload_vram(base_url=base_url)
            
        self.llm = self._get_llm(self.llm_config)
        self.manager_llm = self._get_llm(self.llm_config.get('manager', self.llm_config))
        
        # Load Tools
        self.file_tools = [FileTools.write_file, FileTools.read_file, FileTools.list_files, FileTools.create_directory]
        self.shell_tools = [ShellTools.execute_command]
        self.test_tools = [TestTools.run_tests]
        
        # Load MCP Tools (SQLite)
        try:
            self.mcp_loader = MCPLoader()
            self.sqlite_server = self.mcp_loader.load_server("sqlite")
            # We need to verify how to get tools from the adapter. 
            # In CrewAI, we can pass the adapter instance directly in the 'tools' list if supported, 
            # or use `adapter.get_tools()`. 
            # The manual says: "When using MCPServerAdapter with CrewAI, use it as a context manager ... to retrieve the list of tools."
            # However, since we want agents to persist, we might need to handle the context manager differently.
            # For now, let's assume we use it in the Crew definition or tasks, but agents need the tools list.
            # A common pattern is to wrap the adapter usage.
            # But let's try to just instantiate it here. 
            # Note: MCPServerAdapter might need to be entered (__enter__) to connect.
            pass
        except Exception as e:
            print(f"Warning: Could not load MCP server: {e}")
            self.sqlite_server = None

    def _get_llm(self, config_section):
        """Factory to create LLM instance based on config."""
        provider = config_section.get("provider", "openai")
        
        if provider == "openai":
            # Assuming env var is set or passed
            return LLM(model=config_section.get("openai", {}).get("model", "gpt-4o"))
        
        elif provider == "ollama":
            cfg = config_section.get("ollama", {})
            model = cfg.get('model') or config_section.get('model')
            base_url = (
                cfg.get("base_url")
                or config_section.get("base_url")
                or os.environ.get("OLLAMA_BASE_URL")
                or "http://localhost:11434"
            )
            base_url = base_url.rstrip("/")
            if base_url.endswith("/v1"):
                base_url = base_url[:-3]
            
            return LLM(
                model=f"ollama/{model}",
                base_url=base_url
            )
        
        elif provider == "openrouter":
            cfg = config_section.get("openrouter", {})
            model = config_section.get("model") or cfg.get("model") or "google/gemini-2.5-flash-lite"
            model = os.environ.get("OPENROUTER_MODEL") or model
            model = STALE_OPENROUTER_MODELS.get(model, model)
            if model and not model.startswith("openrouter/"):
                model = f"openrouter/{model}"
            api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
            if api_key and not os.environ.get("OPENROUTER_API_KEY"):
                os.environ["OPENROUTER_API_KEY"] = api_key
            os.environ.pop("OPENAI_API_BASE", None)
            return LLM(
                model=model,
                api_key=api_key,
            )
            
        return LLM(model="gpt-4o") # Default

    def project_manager(self):
        return Agent(
            role='Project Manager',
            goal='Ensure the software project is delivered on time, meets requirements, and is high quality.',
            backstory='You are a seasoned software project manager. You break down high-level requirements into actionable plans. You oversee the development process and ensure the team adheres to the plan.',
            llm=self.manager_llm,
            tools=[], # Manager usually delegates, but might need read access
            allow_delegation=False,
            verbose=True
        )

    def solution_architect(self):
        return Agent(
            role='Solution Architect',
            goal='Design the technical architecture and file structure for the project.',
            backstory='You are an expert software architect. You decide which files are needed, how they interact, and what libraries to use. You create the blueprint for the developers.',
            llm=self.llm,
            tools=self.file_tools, # Needs to see files to know what exists
            verbose=True
        )

    def senior_developer(self):
        # We need to handle tool access carefully. 
        # If we use MCP adapter, we need to make sure it's active when the agent runs.
        # We will handle this in the Task or Flow.
        return Agent(
            role='Senior Developer',
            goal='Implement the software solution according to the architecture and requirements.',
            backstory='You are a top-tier developer. You write clean, efficient, and well-documented code. You follow the specifications provided by the Architect.',
            llm=self.llm,
            tools=self.file_tools,
            verbose=True
        )

    def qa_engineer(self):
        return Agent(
            role='QA Engineer',
            goal='Validate the software quality through rigorous testing. You ALWAYS check exit codes.',
            backstory='You are a detail-oriented QA engineer. You write unit tests and integration tests to break the code. You ensure nothing ships with bugs. You trust the exit code of the test command above all else.',
            llm=self.llm,
            tools=self.file_tools + self.shell_tools + self.test_tools, # Run tests
            verbose=True
        )

    def technical_writer(self):
        return Agent(
            role='Technical Writer',
            goal='Create comprehensive documentation for the project.',
            backstory='You are a skilled technical writer. You explain complex systems clearly. You write READMEs that make it easy for users to understand and use the software.',
            llm=self.llm,
            tools=self.file_tools,
            verbose=True
        )
