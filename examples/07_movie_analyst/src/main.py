import os
import sys
import yaml
import time
import requests
import logging
from dotenv import load_dotenv
from crewai import Crew, Process, LLM

# Setup logging
logging.basicConfig(
    filename='execution.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add repo root to path to import src.mcp_loader
# current file is in examples/07_movie_analyst/src/
# repo root is ../../../
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(repo_root)

# Check if mcp_loader exists
if not os.path.exists(os.path.join(repo_root, "src", "mcp_loader.py")):
    print(f"Error: mcp_loader.py not found at {os.path.join(repo_root, 'src', 'mcp_loader.py')}")
    sys.exit(1)

from src.mcp_loader import MCPLoader
from agents import MovieAnalystAgents
from tasks import MovieAnalystTasks

def clear_ollama_vram(base_url="http://localhost:11434"):
    """
    Attempts to unload models from Ollama to clear VRAM.
    """
    print("🧹 Attempting to clear Ollama VRAM...")
    try:
        # To unload a model in Ollama, we can generate a request with keep_alive=0
        # We try to unload common models we might have used
        models_to_unload = ["llama3", "llama3.2", "mistral", "gemma"]
        
        for model in models_to_unload:
            try:
                # We don't care about the prompt, just the keep_alive parameter
                payload = {
                    "model": model,
                    "prompt": "",
                    "keep_alive": 0
                }
                response = requests.post(f"{base_url}/api/generate", json=payload, timeout=2)
                if response.status_code == 200:
                    print(f"   Requested unload for {model}")
            except Exception:
                pass # Model might not be loaded or name is wrong, ignore
        
        print("   VRAM cleanup signal sent.")
    except Exception as e:
        print(f"   Warning: Could not contact Ollama to clear VRAM: {e}")

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "preferences.yaml")
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}")
        return None
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_llm_instance(config):
    """
    Creates and returns the LLM instance based on configuration.
    """
    llm_config = config.get("llm_config", {})
    selected_profile_name = llm_config.get("selected", "openai")
    
    print(f"🧠 Selected LLM Profile: {selected_profile_name}")
    
    profiles = llm_config.get("profiles", {})
    profile = profiles.get(selected_profile_name)
    
    if not profile:
        print(f"Warning: Profile '{selected_profile_name}' not found in profiles. Falling back to default OpenAI.")
        return None # CrewAI defaults to OpenAI gpt-4 if None

    provider = profile.get("provider", "").lower()
    model = profile.get("model")
    base_url = profile.get("base_url")
    
    if provider == "ollama":
        # For Ollama, we use the standard OpenAI-compatible endpoint usually, 
        # but CrewAI has a specific way or we can use the generic LLM class.
        # CrewAI's LLM class supports 'ollama/model_name' format or custom base_url.
        print(f"   Using Ollama: {model} at {base_url}")
        return LLM(
            model=f"ollama/{model}",
            base_url=base_url
        )
        
    elif provider == "openai":
        # Standard OpenAI
        print(f"   Using OpenAI: {model}")
        return LLM(model=model)
        
    elif provider == "openrouter":
        # OpenRouter
        print(f"   Using OpenRouter: {model}")
        return LLM(
            model=model,
            base_url=base_url,
            api_key=os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        )
    
    return None

def run():
    print("Starting Example 07: Movie Analyst (Advanced)")
    
    # Load env
    load_dotenv(os.path.join(repo_root, ".env"), override=True)
    
    # Load Config
    config = load_config()
    if not config:
        print("Failed to load configuration.")
        return

    print(f"Target Criteria: {config['movie_criteria']}")
    print(f"User Context: {config['user_context']}")
    print(f"Report Preferences: {config.get('report_preferences', {})}")

    # Setup LLM
    llm = get_llm_instance(config)

    # Load MCP Tools
    config_path = os.path.join(repo_root, "crewai_mcp.json")
    loader = MCPLoader(config_path)
    
    # Get tools from MCP servers
    print("Loading MCP Tools...")
    
    jw_tools = []
    bs_tools = []
    fetch_tools = []
    
    try:
        # Load JustWatch
        jw_adapter = loader.load_server("justwatch")
        jw_tools = jw_adapter.tools if hasattr(jw_adapter, 'tools') else []
        print(f"Loaded {len(jw_tools)} JustWatch tools.")

        # Load Brave Search
        bs_adapter = loader.load_server("brave-search")
        bs_tools = bs_adapter.tools if hasattr(bs_adapter, 'tools') else []
        print(f"Loaded {len(bs_tools)} Brave Search tools.")

        # Load Multi-Fetch (or fetch)
        try:
            # Try Multi-Fetch as requested by user
            mf_adapter = loader.load_server("Multi-Fetch")
            fetch_tools = mf_adapter.tools if hasattr(mf_adapter, 'tools') else []
            print(f"Loaded {len(fetch_tools)} Multi-Fetch tools.")
        except Exception as e_mf:
            print(f"Multi-Fetch not found or failed, trying standard fetch: {e_mf}")
            try:
                f_adapter = loader.load_server("fetch")
                fetch_tools = f_adapter.tools if hasattr(f_adapter, 'tools') else []
                print(f"Loaded {len(fetch_tools)} Fetch tools.")
            except Exception as e_f:
                print(f"Fetch tools also failed: {e_f}")
        
    except Exception as e:
        print(f"Error loading MCP servers: {e}")

    if not jw_tools and not bs_tools and not fetch_tools:
        print("Warning: No tools loaded. The agents might fail.")

    agents = MovieAnalystAgents()
    tasks = MovieAnalystTasks()

    # Create Agents with selected LLM
    curator = agents.movie_curator(bs_tools, llm)
    streaming_specialist = agents.streaming_specialist(jw_tools, llm)
    link_verifier = agents.link_verifier(bs_tools + fetch_tools, llm) # Uses search AND fetch tools
    reporter = agents.reporter(llm)

    # Create Tasks
    recommend_task = tasks.recommend_movies(curator, config['movie_criteria'])
    availability_task = tasks.check_availability(streaming_specialist, recommend_task, config['user_context'])
    verify_task = tasks.verify_links(link_verifier, availability_task, config['user_context'])
    guide_task = tasks.compile_guide(reporter, verify_task, config.get('report_preferences', {}))

    # Create Crew
    crew = Crew(
        agents=[curator, streaming_specialist, link_verifier, reporter],
        tasks=[recommend_task, availability_task, verify_task, guide_task],
        process=Process.sequential,
        verbose=True,
        max_rpm=10 # Limit requests per minute to avoid rate limits
    )

    print("Kickoff Crew...")
    clear_ollama_vram(base_url=config.get("llm_config", {}).get("profiles", {}).get("ollama", {}).get("base_url", "http://localhost:11434"))
    
    result = crew.kickoff()
    print("######################")
    print(result)

    # Save result to file
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "outputs")
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "Movie_Guide_Report.md")
    
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(str(result))
    
    print(f"Report saved to {output_file}")

if __name__ == "__main__":
    run()
