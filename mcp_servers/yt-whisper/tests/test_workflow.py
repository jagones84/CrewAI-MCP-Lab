import subprocess
import sys
import os
from pathlib import Path

def test_workflow():
    # Setup paths
    project_root = Path(__file__).parent.parent
    transcribe_script = project_root / "transcribe.py"
    
    # Test parameters
    youtube_url = "https://www.youtube.com/watch?v=hCmEoFuj0Yo"
    output_audio = project_root / "tests" / "test_5min_asmr_accelerated.m4a"
    output_text = project_root / "tests" / "test_5min_asmr_accelerated.txt"
    start_time = "00:00:00"
    end_time = "00:05:00"  # Test with 5 minutes as requested
    model = "tiny"        # Using tiny for faster test execution
    
    # Use the venv python
    python_exe = sys.executable
    
    print(f"Running 5-minute accelerated workflow test with timing...")
    cmd = [
        python_exe,
        str(transcribe_script),
        youtube_url,
        "--output_audio", str(output_audio),
        "--output_text", str(output_text),
        "--start", start_time,
        "--to", end_time,
        "--model", model
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("STDOUT:", result.stdout)
        
        if output_audio.exists():
            print(f"SUCCESS: Audio file created at {output_audio}")
        else:
            print(f"FAILURE: Audio file not found at {output_audio}")
            
        if output_text.exists():
            print(f"SUCCESS: Transcription file created at {output_text}")
            with open(output_text, 'r', encoding='utf-8') as f:
                content = f.read()
                print(f"Transcription content: {content[:100]}...")
        else:
            print(f"FAILURE: Transcription file not found at {output_text}")
            
    except subprocess.CalledProcessError as e:
        print(f"Workflow failed with error code {e.returncode}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)

if __name__ == "__main__":
    test_workflow()
