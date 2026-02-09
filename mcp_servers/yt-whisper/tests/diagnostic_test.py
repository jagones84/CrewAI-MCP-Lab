import sys
import os
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from transcribe import run_transcription_workflow

def diagnostic_test():
    # Test parameters from user's request
    youtube_url = "https://www.youtube.com/watch?v=L6OYgYVi2Ug"
    output_audio = project_root / "output" / "diag_test.m4a"
    output_text = project_root / "output" / "diag_test.txt"
    start_time = "00:00:00"
    end_time = "00:00:10"  # 10 seconds only
    model = "tiny"        # Tiny for speed
    
    print(f"Starting diagnostic test for: {youtube_url}")
    print(f"Duration: {start_time} to {end_time}")
    print(f"Model: {model}")
    
    try:
        transcript = run_transcription_workflow(
            youtube_url, 
            str(output_audio), 
            str(output_text), 
            start_time, 
            end_time, 
            model, 
            use_cuda=False # Use CPU for diagnostics to avoid GPU issues
        )
        print("\nDIAGNOSTIC SUCCESS!")
        print(f"Transcript length: {len(transcript)}")
        print(f"Preview: {transcript[:100]}")
    except Exception as e:
        print(f"\nDIAGNOSTIC FAILED!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    diagnostic_test()
