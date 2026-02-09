import os
import sys
from dotenv import load_dotenv
from crewai import Crew, Process

# Add repo root to path to import src.mcp_loader
# current file is in examples/06_youtube_researcher/src/
# repo root is ../../../
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(repo_root)

# Check if mcp_loader exists
if not os.path.exists(os.path.join(repo_root, "src", "mcp_loader.py")):
    print(f"Error: mcp_loader.py not found at {os.path.join(repo_root, 'src', 'mcp_loader.py')}")
    sys.exit(1)

from src.mcp_loader import MCPLoader
from agents import YoutubeResearcherAgents
from tasks import YoutubeResearcherTasks

def run():
    print("Starting Example 06: YouTube Researcher")
    
    # Load env
    load_dotenv(os.path.join(repo_root, ".env"), override=True)
    
    # Load MCP Tools
    config_path = os.path.join(repo_root, "crewai_mcp.json")
    loader = MCPLoader(config_path)
    
    # Get tools from MCP servers
    print("Loading MCP Tools...")
    try:
        # Load DuckDuckGo
        ddg_adapter = loader.load_server("DuckDuckGo Search Server")
        ddg_tools = ddg_adapter.tools if hasattr(ddg_adapter, 'tools') else []
        print(f"Loaded {len(ddg_tools)} search tools.")

        # Load YT Whisper
        yt_adapter = loader.load_server("yt-whisper")
        yt_tools = yt_adapter.tools if hasattr(yt_adapter, 'tools') else []
        print(f"Loaded {len(yt_tools)} transcription tools.")
        
    except Exception as e:
        print(f"Error loading MCP servers: {e}")
        # Continue if possible? No, we need tools.
        # But maybe one loaded.
        if 'ddg_tools' not in locals(): ddg_tools = []
        if 'yt_tools' not in locals(): yt_tools = []
        # return

    agents = YoutubeResearcherAgents()
    tasks = YoutubeResearcherTasks()

    # Create Agents
    researcher = agents.researcher(ddg_tools)
    transcriber = agents.transcriber(yt_tools)
    summarizer = agents.summarizer()

    # Create Tasks
    find_videos = tasks.find_videos(researcher)
    transcribe_videos = tasks.transcribe_videos(transcriber, find_videos)
    summarize_videos = tasks.summarize_videos(summarizer, transcribe_videos)

    # Create Crew
    crew = Crew(
        agents=[researcher, transcriber, summarizer],
        tasks=[find_videos, transcribe_videos, summarize_videos],
        process=Process.sequential,
        verbose=True
    )

    print("Kickoff Crew...")
    result = crew.kickoff()
    print("######################")
    print(result)

if __name__ == "__main__":
    run()
