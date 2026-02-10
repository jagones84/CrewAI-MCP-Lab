import os
import sys
import yaml
import logging
from dotenv import load_dotenv
from crewai import Crew, Process, LLM

# Setup paths
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from utils.mcp_loader import MCPLoader
from agents import FinancialAgents
from tasks import FinancialTasks

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_config():
    config_path = os.path.join(os.path.dirname(current_dir), "config", "preferences.yaml")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

def get_llm(config):
    llm_conf = config.get("llm", {})
    provider = llm_conf.get("provider", "ollama")
    model = llm_conf.get("model", "llama3")
    base_url = llm_conf.get("base_url", "http://localhost:11434")
    
    if provider == "ollama":
        return LLM(model=f"ollama/{model}", base_url=base_url)
    else:
        # Fallback or other providers
        return LLM(model=model)

def main():
    load_dotenv()
    config = load_config()
    
    # 1. Load MCP Tools
    loader = MCPLoader()
    try:
        yfinance_adapter = loader.load_server("yfinance")
    except Exception as e:
        logger.error(f"Failed to load MCP server: {e}")
        return

    # 2. Setup Agents & Run Crew
    # Use the adapter as a context manager to automatically handle start/stop
    with yfinance_adapter as financial_tools:
        llm = get_llm(config)
        agents = FinancialAgents(llm)
        
        data_collector = agents.data_collector()
        # Assign the loaded tools to the agent
        data_collector.tools = financial_tools
        
        analyst = agents.financial_analyst()
        reporter = agents.reporter()

        # 3. Setup Tasks
        tasks = FinancialTasks()
        
        tickers = config.get("stocks", {}).get("default_tickers", ["AAPL"])
        
        # Ensure output directory exists
        output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(output_dir, exist_ok=True)
        report_path = os.path.join(output_dir, "financial_report.md")

        task1 = tasks.collect_data_task(data_collector, tickers)
        task2 = tasks.analyze_data_task(analyst)
        task3 = tasks.write_report_task(reporter, report_path)

        # 4. Create Crew
        crew = Crew(
            agents=[data_collector, analyst, reporter],
            tasks=[task1, task2, task3],
            process=Process.sequential,
            verbose=True
        )

        result = crew.kickoff()
        print("######################")
        print(result)

if __name__ == "__main__":
    main()
