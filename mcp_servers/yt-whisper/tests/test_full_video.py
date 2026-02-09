import sys
import os
import time
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server import transcribe_youtube_video

def test_mcp_full_video():
    # User's target video
    youtube_url = "https://www.youtube.com/watch?v=L6OYgYVi2Ug"
    output_name = "antigravity_full_test"
    
    print(f"!!! STARTING FULL VIDEO MCP TEST !!!")
    print(f"URL: {youtube_url}")
    print(f"Output Name: {output_name}")
    print(f"Time: {time.strftime('%H:%M:%S')}")
    print("-" * 50)
    
    start_time = time.time()
    
    try:
        # Testing FULL video (no start/end times)
        # We use medium model as requested by user's initial state
        result = transcribe_youtube_video(
            youtube_url=youtube_url, 
            output_name=output_name,
            model="medium",
            use_cuda=True
        )
        
        elapsed = time.time() - start_time
        print(f"\n!!! TEST COMPLETED !!!")
        print(f"Total Time: {elapsed:.2f} seconds")
        print("-" * 50)
        print(result)
        print("-" * 50)

    except Exception as e:
        print(f"\n!!! TEST FAILED !!!")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_full_video()
