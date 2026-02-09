import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server import transcribe_youtube_video

def test_mcp_function():
    # Test parameters mirroring the user's request
    youtube_url = "https://www.youtube.com/watch?v=L6OYgYVi2Ug"
    output_name = "antigravity_video_test"
    
    print(f"Testing MCP Tool: transcribe_youtube_video")
    print(f"URL: {youtube_url}")
    print(f"Output Name: {output_name}")
    
    try:
        # We don't specify language here to test the default behavior (auto-detect)
        # Full video transcription
        # Rely on new server defaults (small model, beam_size=1)
        result = transcribe_youtube_video(
            youtube_url=youtube_url, 
            output_name=output_name,
            start_time="00:00:00",
            end_time=None
        )
        print("\nMCP Tool Call Result:")
        print("-" * 50)
        print(result)
        print("-" * 50)
        
        # Verify output file exists
        output_path = project_root / "output" / f"{output_name}.txt"
        if output_path.exists():
             print(f"\nSUCCESS: Output file found at {output_path}")
        else:
             print(f"\nFAILURE: Output file NOT found at {output_path}")

    except Exception as e:
        print(f"\nMCP Tool Call FAILED!")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_function()
