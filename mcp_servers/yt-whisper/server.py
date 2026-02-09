import sys
import os
import time

# Explicitly add current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from mcp.server.fastmcp import FastMCP
from pathlib import Path
from transcribe import run_transcription_workflow

# Initialize MCP Server
mcp = FastMCP("yt-whisper")
DEFAULT_OUTPUT_DIR = os.path.join(current_dir, "output")

@mcp.tool()
def transcribe_youtube_video(
    youtube_url: str,
    output_name: str = "transcription",
    output_path: str = DEFAULT_OUTPUT_DIR,
    start_time: str = "00:00:00",
    end_time: str = None,
    model: str = "small",
    use_cuda: bool = True,
    language: str = None,
    beam_size: int = 1
) -> str:
    """
    Download audio from YouTube (optimized for speed) and transcribe it using Whisper.

    Args:
        youtube_url: The URL of the YouTube video.
        output_name: Base name for the output files (saved as output_name.m4a and output_name.txt).
        output_path: Optional custom directory to save files in. Defaults to server's 'output' folder.
        start_time: Start timestamp (HH:MM:SS) for the segment.
        end_time: End timestamp (HH:MM:SS) for the segment (Optional).
        model: Whisper model size (tiny, base, small, medium, large). Default is 'small' for speed.
        use_cuda: Whether to use GPU acceleration (default: True).
        language: Language code (e.g., 'en', 'it'). If None, Whisper auto-detects.
        beam_size: Beam size for transcription. Default is 1 (greedy search) for speed.
    """
    try:
        print(f"Tool called with URL: {youtube_url}", file=sys.stderr)
        # Define output paths
        output_dir = Path(output_path)
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Sanitize output name
        safe_name = "".join([c for c in output_name if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).rstrip()
        if not safe_name:
            safe_name = "output"
            
        output_audio = str(output_dir / f"{safe_name}.m4a")
        output_text = str(output_dir / f"{safe_name}.txt")

        # Run workflow
        transcript = run_transcription_workflow(
            youtube_url, 
            output_audio, 
            output_text, 
            start_time, 
            end_time, 
            model, 
            use_cuda,
            language,
            beam_size
        )

        return f"Success! Transcription saved to {output_text}\n\nPreview:\n{transcript[:500]}..."

    except Exception as e:
        return f"Error processing video: {str(e)}"

if __name__ == "__main__":
    print("Starting yt-whisper MCP Server...", file=sys.stderr)
    mcp.run()
