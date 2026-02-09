import sys
import os
import yaml
from crewai import Agent, Crew, Process, Task, LLM

# Add project root to sys.path to import src.mcp_loader
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.append(project_root)

try:
    from src.mcp_loader import MCPLoader
except ImportError:
    # Fallback if running from a different context
    sys.path.append(os.path.join(project_root, "src"))
    from mcp_loader import MCPLoader

def load_config(file_path):
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

def main():
    print("Starting MCP Workflow Test...")
    
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
        # The server name in crewai_mcp.json is "DuckDuckGo Search Server"
        ddg_server = loader.load_server("DuckDuckGo Search Server")
        search_tools = ddg_server.tools
        print(f"Loaded {len(search_tools)} tools from DuckDuckGo Search Server")
    except Exception as e:
        print(f"Error loading MCP tools: {e}")
        # Continue without tools to test agent creation at least, but tasks will fail if they need tools
        pass

    if not search_tools:
        print("Warning: No search tools loaded. Agents might fail if they rely on them.")

    # Configure LLM (Using local Ollama as OpenRouter seems out of quota)
    # Model from user's previous config
    ollama_llm = LLM(
        model="ollama/huihui_ai/glm-4.7-flash-abliterated:latest",
        base_url="http://10.0.0.1:11434"
    )

    # Define Agents
    researcher = Agent(
        role=agents_config['researcher']['role'],
        goal=agents_config['researcher']['goal'].format(topic="AI Agents in 2025"),
        backstory=agents_config['researcher']['backstory'],
        verbose=True,
        allow_delegation=False,
        tools=search_tools,
        llm=ollama_llm
    )

    writer = Agent(
        role=agents_config['writer']['role'],
        goal=agents_config['writer']['goal'].format(topic="AI Agents in 2025"),
        backstory=agents_config['writer']['backstory'],
        verbose=True,
        allow_delegation=False,
        llm=ollama_llm
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
