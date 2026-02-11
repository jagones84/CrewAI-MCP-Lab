import os
import sys
import yaml
from dotenv import load_dotenv
from crewai import Crew, Process

# Add repo root to path to import src.mcp_loader
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(repo_root)
# Add src to path for local imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Check if mcp_loader exists
if not os.path.exists(os.path.join(repo_root, "src", "mcp_loader.py")):
    print(f"Error: mcp_loader.py not found at {os.path.join(repo_root, 'src', 'mcp_loader.py')}")
    sys.exit(1)

from src.mcp_loader import MCPLoader
from agents import MarketingAgents
from tasks import MarketingTasks
from config.config import ConfigLoader
from utils.logger import setup_logging
from utils.comfy_check import check_comfyui_connection

def run():
    """
    Main entry point for Example 09: Marketing Strategy Campaign.
    """
    # 1. Setup Logging
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "log", "log.txt")
    logger = setup_logging(log_path)
    logger.info("Starting Example 09: Marketing Strategy Campaign")
    
    # 2. Load env
    load_dotenv(os.path.join(repo_root, ".env"), override=True)
    
    # 3. Load Preferences
    config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "preferences.yaml")
    try:
        preferences = ConfigLoader.load_config(config_path)
        logger.info(f"Loaded preferences from {config_path}")
    except Exception as e:
        logger.error(f"Failed to load preferences: {e}")
        sys.exit(1)

    # 3.5. Manage LLM Server (Ollama/LlamaCpp)
    llm_root = preferences.get('llm', {})
    provider = llm_root.get('provider', 'openai')
    llm_controller = None

    if provider in ['ollama', 'llamacpp']:
        try:
            from utils.llm_controllers import OllamaController, LlamaController
            
            provider_config = llm_root.get(provider, {})
            # Ensure critical keys exist or fallback to root (though preferences structure separates them)
            
            if provider == 'ollama':
                logger.info("Initializing Ollama Controller...")
                llm_controller = OllamaController(provider_config)
            elif provider == 'llamacpp':
                logger.info("Initializing LlamaCpp Controller...")
                llm_controller = LlamaController(provider_config)
                
            if llm_controller:
                logger.info(f"Starting {provider} server...")
                if not llm_controller.start_server():
                    logger.error(f"Failed to start {provider} server. Please check your configuration and logs.")
                    sys.exit(1)
                
                # Register cleanup
                import atexit
                atexit.register(llm_controller.stop_server)
                
        except Exception as e:
            logger.error(f"Error managing local LLM server: {e}")
            sys.exit(1)

    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), preferences.get('outputs', {}).get('dir', 'outputs'))
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 3.6 Manage ComfyUI Server
    comfy_config = preferences.get('comfyui', {})
    if comfy_config:
        try:
            from utils.comfy_controller import ComfyController
            comfy_controller = ComfyController(comfy_config)
            
            # Check if running or needs start
            if not comfy_controller.check_server_status():
                 if comfy_config.get('install_path'):
                     logger.info("Starting ComfyUI server...")
                     if comfy_controller.start_server():
                         import atexit
                         atexit.register(comfy_controller.stop_server)
                     else:
                         logger.warning("Failed to auto-start ComfyUI. Image generation might fail.")
                 else:
                     # Just log, we'll check connection next
                     pass
        except Exception as e:
            logger.error(f"Error initializing ComfyController: {e}")

    # Pre-flight Check: ComfyUI
    comfy_host = os.environ.get("COMFYUI_SERVER_ADDRESS", "127.0.0.1:8188").split(":")[0]
    comfy_port = int(os.environ.get("COMFYUI_SERVER_ADDRESS", "127.0.0.1:8188").split(":")[1])
    
    if check_comfyui_connection(comfy_host, comfy_port):
        logger.info("✅ ComfyUI is reachable.")
    else:
        logger.warning("⚠️  ComfyUI is NOT reachable. Image generation task will likely fail.")
        logger.warning("Please ensure ComfyUI is running at " + f"{comfy_host}:{comfy_port}")

    # 4. Load MCP Tools
    mcp_config_path = os.path.join(repo_root, "crewai_mcp.json")
    loader = MCPLoader(mcp_config_path)
    
    logger.info("Loading MCP Tools...")
    try:
        # Load DuckDuckGo
        ddg_adapter = loader.load_server("DuckDuckGo Search Server")
        ddg_tools = ddg_adapter.tools if hasattr(ddg_adapter, 'tools') else []
        logger.info(f"Loaded {len(ddg_tools)} search tools.")

        # Load ComfyUI
        comfy_adapter = loader.load_server("comfyui")
        comfy_tools = comfy_adapter.tools if hasattr(comfy_adapter, 'tools') else []
        logger.info(f"Loaded {len(comfy_tools)} image generation tools.")
        
    except Exception as e:
        logger.error(f"Error loading MCP servers: {e}")
        # We need these tools
        pass

    if 'ddg_tools' not in locals(): ddg_tools = []
    if 'comfy_tools' not in locals(): comfy_tools = []

    # 5. Initialize Agents and Tasks
    agents_manager = MarketingAgents(preferences)
    tasks_manager = MarketingTasks()

    # Create Agents
    researcher = agents_manager.market_researcher(ddg_tools)
    strategist = agents_manager.creative_strategist()
    designer = agents_manager.visual_designer(comfy_tools)

    # Input (could be from user or hardcoded for example)
    product_description = "A smart coffee mug that keeps coffee at the perfect temperature and tracks caffeine intake via an app."
    logger.info(f"Target Product: {product_description}")

    # Create Tasks
    research_output = os.path.join(output_dir, "research.md")
    strategy_output = os.path.join(output_dir, "strategy.md")
    
    research_task = tasks_manager.research_product(researcher, product_description, output_file=research_output)
    strategy_task = tasks_manager.develop_strategy(strategist, [research_task], output_file=strategy_output)
    image_task = tasks_manager.generate_campaign_image(designer, [strategy_task], output_dir)

    # Create Crew
    crew = Crew(
        agents=[researcher, strategist, designer],
        tasks=[research_task, strategy_task, image_task],
        process=Process.sequential,
        verbose=True
    )

    logger.info("Kickoff Crew...")
    result = crew.kickoff()
    
    logger.info("Crew Execution Completed")
    logger.info(f"Results saved in {output_dir}")
    print("######################")
    print(result)

if __name__ == "__main__":
    run()
