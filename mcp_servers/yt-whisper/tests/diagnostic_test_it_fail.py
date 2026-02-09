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
    output_audio = project_root / "output" / "diag_test_it_fail.m4a"
    output_text = project_root / "output" / "diag_test_it_fail.txt"
    start_time = "00:00:00"
    end_time = "00:00:30"  # 30 seconds
    model = "medium"
    
    print(f"Starting diagnostic test (FORCING ITALIAN ON ENGLISH VIDEO): {youtube_url}")
    
    try:
        # Forcing Italian as it was in the original code
        transcript = run_transcription_workflow(
            youtube_url, 
            str(output_audio), 
            str(output_text), 
            start_time, 
            end_time, 
            model, 
            use_cuda=True,
            language="it" 
        )
        print("\nDIAGNOSTIC SUCCESS (surprisingly)!")
        print(f"Transcript length: {len(transcript)}")
        print(f"Preview: {transcript[:100]}")
    except Exception as e:
        print(f"\nDIAGNOSTIC FAILED!")
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")

if __name__ == "__main__":
    diagnostic_test()
