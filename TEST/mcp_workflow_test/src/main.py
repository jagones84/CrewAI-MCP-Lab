import sys
import os
import yaml
import argparse
from dotenv import load_dotenv

# Load environment variables early with override to ensure .env values take precedence
load_dotenv(override=True)

from crewai import Agent, Crew, Process, Task, LLM
from crewai_tools import PDFSearchTool

"""
USAGE INSTRUCTIONS:

1. Configure your environment in .env:
   - For Llama.cpp: Set LLAMACPP_EXE, LLAMACPP_MODELS_DIR, LLAMACPP_MODEL
   - For Ollama: Set OLLAMA_MODEL, OLLAMA_BASE_URL
   - For OpenRouter: Set OPENAI_API_KEY, OPENROUTER_MODEL

2. Run the script with a provider argument:
   - python main.py --provider ollama      (Default)
   - python main.py --provider llama_cp    (Uses local Llama.cpp server)
   - python main.py --provider openrouter  (Uses OpenRouter API)

3. Or run interactively:
   - python main.py
"""

# Add project root to sys.path to import src.mcp_loader
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

try:
    from src.mcp_loader import MCPLoader
    from src.services.ollama_controller import OllamaController
    from src.services.llama_controller import LlamaController
except ImportError:
    # Fallback if running from a different context
    sys.path.append(os.path.join(project_root, "src"))
    from mcp_loader import MCPLoader
    from services.ollama_controller import OllamaController
    from services.llama_controller import LlamaController

def load_config(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def get_llm_provider():
    """
    Determines the LLM provider based on CLI args or user input.
    Defaults to 'ollama' if not specified or interactive.
    """
    parser = argparse.ArgumentParser(description="Run MCP Workflow Test")
    parser.add_argument("--provider", choices=["ollama", "llama_cp", "openrouter"], help="LLM Provider to use")
    # Allow other args to be passed without erroring (crewai might use some)
    args, _ = parser.parse_known_args()

    if args.provider:
        return args.provider

    print("\nSelect LLM Provider:")
    print("1. Ollama (default)")
    print("2. Llama.cpp")
    print("3. OpenRouter")
    
    # Check if we are in an interactive environment where input is possible
    # For this automated environment, we default to ollama if input is empty
    if sys.stdin.isatty():
        try:
            choice = input("Enter choice [1/2/3]: ").strip()
            if choice == "2":
                return "llama_cp"
            elif choice == "3":
                return "openrouter"
        except (EOFError, OSError, KeyboardInterrupt):
            pass
    else:
        print("Non-interactive session detected. Defaulting to Ollama.")
    
    return "ollama"

def main():
    print("Starting MCP Workflow Test...")
    
    # --- CONFIGURATION ---
    llm_provider = get_llm_provider()
    print(f"👉 Using Provider: {llm_provider}")
    # ---------------------
    
    # Paths
    current_dir = os.path.dirname(__file__)
    config_dir = os.path.join(current_dir, "../config")
    agents_config = load_config(os.path.join(config_dir, "agents.yaml"))
    tasks_config = load_config(os.path.join(config_dir, "tasks.yaml"))
    mcp_config_path = os.path.join(project_root, "crewai_mcp.json")

    # Load MCP Tools
    print(f"Loading MCP config from: {mcp_config_path}")
    loader = MCPLoader(mcp_config_path)
    
    search_tools = []
    try:
        # Load DuckDuckGo Search Server tools
        ddg_server = loader.load_server("DuckDuckGo Search Server")
        search_tools = ddg_server.tools
        print(f"Loaded {len(search_tools)} tools from DuckDuckGo Search Server")
        
        # PROACTIVE FIX: Remove generic 'fetch_content' if present to avoid PDF binary dumps
        # Agents should use specialized tools for content fetching
        original_count = len(search_tools)
        search_tools = [t for t in search_tools if t.name != "fetch_content"]
        if len(search_tools) < original_count:
            print(f"⚠️  Filtered out 'fetch_content' tool to prevent binary output issues.")
            
    except Exception as e:
        print(f"Error loading MCP tools: {e}")
        pass

    if not search_tools:
        print("Warning: No search tools loaded. Agents might fail if they rely on them.")

    # Initialize PDF Tool for better PDF handling
    print("Initializing PDFSearchTool...")
    pdf_tool = PDFSearchTool()

    # Combine all tools
    agent_tools = search_tools + [pdf_tool]

    # Configure LLM
    selected_llm = None

    if llm_provider == "ollama":
        ollama_config = {
            "model": os.getenv("OLLAMA_MODEL", "llama3:latest"),
            "base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        }
        print(f"⚙️  Initializing Ollama Manager with model: {ollama_config['model']}...")
        ollama_manager = OllamaController(ollama_config)
        ollama_manager.start_server()
        ollama_manager.load_model()

        selected_llm = LLM(
            model=f"ollama/{ollama_config['model']}",
            base_url="http://localhost:11434"
        )
    
    elif llm_provider == "llama_cp":
        # Allow env vars to override these defaults
        llama_config = {
            "model": os.getenv("LLAMACPP_MODEL", "Llama-3-8B-Abliterated-v3-Q8_0.gguf"), # Updated default to existing model
            "base_url": os.getenv("LLAMACPP_BASE_URL", "http://localhost:8080/v1"),
            "executable_path": os.getenv("LLAMACPP_EXE", r"F:\PROGRAMS\llama_cp\llama-server.exe"),
            "models_dir": os.getenv("LLAMACPP_MODELS_DIR", r"F:\PROGRAMS\llama_cp\MODELS") # Updated default path
        }
        print("⚙️  Initializing LlamaCP Manager...")
        print(f"   👉 Target Model File: {llama_config['model']}")
        llama_manager = LlamaController(llama_config)
        # Only try to ensure server if we have valid paths
        if os.path.exists(llama_config["executable_path"]) and os.path.exists(llama_config["models_dir"]):
            llama_manager.ensure_server_running()
            # Use a generic model name so LiteLLM doesn't try to be too smart with specific templates
            # Llama.cpp server ignores the model name in the request anyway
            selected_llm = LLM(
                model="openai/gpt-3.5-turbo",
                base_url=f"http://{llama_manager.host}:{llama_manager.port}/v1",
                api_key="sk-no-key-required"
            )
        else:
            print("❌ LlamaCP Configuration Missing!")
            print(f"   Executable: {llama_config['executable_path']}")
            print(f"   Models Dir: {llama_config['models_dir']}")
            print("   Please set LLAMACPP_EXE and LLAMACPP_MODELS_DIR env vars or update the script.")
            return

    elif llm_provider == "openrouter":
        print("⚙️  Initializing OpenRouter...")
        # OpenRouter often needs these headers to avoid being blocked
        # and LiteLLM specifically looks for OPENROUTER_API_KEY for the openrouter/ prefix
        openrouter_api_key = os.getenv("OPENAI_API_KEY") 
        if openrouter_api_key:
            os.environ["OPENROUTER_API_KEY"] = openrouter_api_key
            
        # Clear OPENAI_API_BASE to avoid LiteLLM getting confused when using openrouter/ prefix
        if "OPENAI_API_BASE" in os.environ:
            del os.environ["OPENAI_API_BASE"]

        openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001") 

        if not openrouter_api_key:
             print("❌ OpenRouter API Key missing. Please set OPENAI_API_KEY in .env")
             return
             
        if not openrouter_model.startswith("openrouter/"):
            full_model_name = f"openrouter/{openrouter_model}"
        else:
            full_model_name = openrouter_model
            
        print(f"   👉 Model: {full_model_name}")
        
        selected_llm = LLM(
            model=full_model_name,
            api_key=openrouter_api_key,
            # OpenRouter requirements
            extra_headers={
                "HTTP-Referer": "https://github.com/crewAIInc/crewAI", # Standard referer
                "X-Title": "CrewAI MCP Lab"
            }
        )

    if not selected_llm:
        print("❌ No LLM provider selected or configured correctly.")
        return

    # Define Agents
    researcher = Agent(
        role=agents_config['researcher']['role'],
        goal=agents_config['researcher']['goal'].format(topic="AI Agents in 2025"),
        backstory=agents_config['researcher']['backstory'],
        verbose=True,
        allow_delegation=False,
        tools=agent_tools,  # Updated to use combined tools
        llm=selected_llm
    )

    writer = Agent(
        role=agents_config['writer']['role'],
        goal=agents_config['writer']['goal'].format(topic="AI Agents in 2025"),
        backstory=agents_config['writer']['backstory'],
        verbose=True,
        allow_delegation=False,
        tools=agent_tools, # Writer might need to read the PDF too if researcher passes a link
        llm=selected_llm
    )

    # Define Tasks
    task1 = Task(
        description=tasks_config['research_task']['description'].format(topic="AI Agents in 2025"),
        expected_output=tasks_config['research_task']['expected_output'].format(topic="AI Agents in 2025"),
        agent=researcher
    )

    task2 = Task(
        description=tasks_config['writing_task']['description'].format(topic="AI Agents in 2025"),
        expected_output=tasks_config['writing_task']['expected_output'].format(topic="AI Agents in 2025"),
        agent=writer,
        context=[task1]
    )

    # Instantiate Crew
    crew = Crew(
        agents=[researcher, writer],
        tasks=[task1, task2],
        verbose=True,
        process=Process.sequential
    )

    # Kickoff
    print("Kickoff crew...")
    result = crew.kickoff()
    print("\n\n########################")
    print("## Here is the result ##")
    print("########################\n")
    print(result)
    
    # Save output to file
    output_dir = os.path.join(current_dir, "../outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "report.md")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(str(result))
    
    print(f"\nReport saved to: {output_file}")

if __name__ == "__main__":
    main()
