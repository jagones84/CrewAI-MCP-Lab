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
    output_audio = project_root / "output" / "diag_test_medium.m4a"
    output_text = project_root / "output" / "diag_test_medium.txt"
    start_time = "00:00:00"
    end_time = "00:00:30"  # 30 seconds
    model = "medium"       # Use medium as the user likely did
    
    print(f"Starting diagnostic test for: {youtube_url}")
    print(f"Duration: {start_time} to {end_time}")
    print(f"Model: {model}")
    
    try:
        # We explicitly set language=None to let it auto-detect (English)
        # Instead of the previous hardcoded "it"
        transcript = run_transcription_workflow(
            youtube_url, 
            str(output_audio), 
            str(output_text), 
            start_time, 
            end_time, 
            model, 
            use_cuda=True,
            language=None 
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
