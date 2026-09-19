import os
import re
import sys
from dotenv import load_dotenv
from crewai import Crew, Process, Task

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


def extract_youtube_urls(text: str, expected_count: int = 2) -> list[str]:
    """Extract unique YouTube watch URLs from agent output while preserving order."""
    matches = re.findall(r"https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]+", text)
    unique_urls = list(dict.fromkeys(matches))
    return unique_urls[:expected_count]


def transcribe_video_urls(urls: list[str], transcription_tool, output_path: str) -> str:
    """Call the MCP transcription tool directly to avoid CrewAI argument envelope issues."""
    os.makedirs(output_path, exist_ok=True)
    transcripts = []
    for index, url in enumerate(urls, start=1):
        output_name = f"transcription_{index}"
        result = transcription_tool.run(
            youtube_url=url,
            output_name=output_name,
            output_path=output_path,
            language="en",
        )
        transcript_file = os.path.join(output_path, f"{output_name}.txt")
        transcript_text = result
        if os.path.exists(transcript_file):
            with open(transcript_file, "r", encoding="utf-8") as handle:
                transcript_text = handle.read()

        transcripts.append(f"Video {index}: {url}\n{transcript_text}")

    return "\n\n".join(transcripts)

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

    output_path = os.path.join(repo_root, "examples", "06_youtube_researcher", "outputs")
    os.makedirs(output_path, exist_ok=True)

    # Create Agents
    researcher = agents.researcher(ddg_tools)
    transcriber = agents.transcriber(yt_tools)
    summarizer = agents.summarizer()

    # Create search task first
    find_videos = tasks.find_videos(researcher)

    search_crew = Crew(
        agents=[researcher],
        tasks=[find_videos],
        process=Process.sequential,
        verbose=True
    )

    print("Kickoff Search Crew...")
    search_result = search_crew.kickoff()
    urls = extract_youtube_urls(str(search_result), expected_count=2)
    if len(urls) < 2:
        raise RuntimeError(f"Expected 2 YouTube URLs from search task, got {len(urls)}: {urls}")

    transcription_tool = yt_tools[0]
    print("Transcribing videos directly through MCP tool...")
    transcription_text = transcribe_video_urls(urls, transcription_tool, output_path)

    summarize_videos = Task(
        description=(
            "Analyze the transcriptions provided. Write a comprehensive summary of the cancer cure "
            "breakthroughs discussed. Highlight key findings, researchers mentioned, and potential impact.\n\n"
            f"TRANSCRIPTIONS:\n{transcription_text}"
        ),
        expected_output='A detailed summary report of the videos.',
        agent=summarizer
    )

    summary_crew = Crew(
        agents=[summarizer],
        tasks=[summarize_videos],
        process=Process.sequential,
        verbose=True
    )

    print("Kickoff Summary Crew...")
    result = summary_crew.kickoff()
    print("######################")
    print(result)

if __name__ == "__main__":
    run()
