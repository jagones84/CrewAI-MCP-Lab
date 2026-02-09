
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from transcribe import run_transcription_workflow

def test_streaming():
    print("Starting direct transcription test...", file=sys.stderr)
    try:
        # Use a short segment to test streaming quickly
        run_transcription_workflow(
            youtube_url="https://www.youtube.com/watch?v=L6OYgYVi2Ug",
            output_audio="test_stream",
            output_text="test_stream.txt",
            start_time="00:00:00",
            end_time=None # Test full video to see if it hangs or streams
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)

if __name__ == "__main__":
    test_streaming()
