import os
import sys
from pathlib import Path

# Add the server directory to path so we can import transcribe
server_dir = Path(__file__).parent.parent
sys.path.append(str(server_dir))

from transcribe import run_transcription_workflow

def test_transcription():
    # Test with a short video or a specific segment to save time
    url = "https://www.youtube.com/watch?v=bAYj8CPnGEc" # The one from the previous run
    output_dir = server_dir / "tests" / "output"
    output_dir.mkdir(exist_ok=True)
    
    audio_path = str(output_dir / "test_audio.m4a")
    text_path = str(output_dir / "test_text.txt")
    
    print(f"Starting manual test for URL: {url}")
    print(f"Output directory: {output_dir}")
    
    try:
        # Using 'tiny' model for fast verification of GPU usage
        result = run_transcription_workflow(
            youtube_url=url,
            output_audio=audio_path,
            output_text=text_path,
            start_time="00:00:00",
            end_time="00:00:30", # Only 30 seconds
            model_name="tiny",
            use_cuda=True,
            language="en"
        )
        print("\nSUCCESS!")
        print(f"Transcription snippet: {result[:200]}...")
    except Exception as e:
        print(f"\nFAILED: {e}")

if __name__ == "__main__":
    test_transcription()
