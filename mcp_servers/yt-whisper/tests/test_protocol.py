import subprocess
import sys
import json
import os
import threading
from pathlib import Path

# Configuration
PYTHON_EXE = r"f:\MCP\AUDIO\MODELS\RVC-Repo\venv\Scripts\python.exe"
SERVER_SCRIPT = r"f:\MCP\AUDIO\MCP\yt-whisper\server.py"
OUTPUT_NAME = "antigravity_protocol_test"
OUTPUT_DIR = r"f:\MCP\AUDIO\MCP\yt-whisper\output"

def read_stream(stream, prefix):
    """Reads from a stream line by line and prints it."""
    for line in iter(stream.readline, ''):
        print(f"[{prefix}] {line.strip()}", file=sys.stderr)

def main():
    print(f"Starting MCP Server process: {SERVER_SCRIPT}")
    
    # Start the server process
    process = subprocess.Popen(
        [PYTHON_EXE, "-u", SERVER_SCRIPT],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=0  # Unbuffered
    )

    # Start stderr reader in a separate thread to avoid blocking
    stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "SERVER_LOG"))
    stderr_thread.daemon = True
    stderr_thread.start()

    try:
        # 1. Initialize
        print("\n>>> Sending initialize request...")
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "test-client", "version": "1.0"}
            }
        }
        process.stdin.write(json.dumps(init_req) + "\n")
        process.stdin.flush()

        # Read initialize response
        response = process.stdout.readline()
        print(f"<<< Received: {response.strip()}")
        
        # 2. Initialized Notification
        print("\n>>> Sending initialized notification...")
        process.stdin.write(json.dumps({
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }) + "\n")
        process.stdin.flush()

        # 3. Call Tool with a "dirty" URL (backticks and spaces)
        dirty_url = " `https://www.youtube.com/watch?v=L6OYgYVi2Ug` "
        print(f"\n>>> Sending tools/call request with dirty URL: {dirty_url}")
        call_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "transcribe_youtube_video",
                "arguments": {
                    "youtube_url": dirty_url,
                    "output_name": OUTPUT_NAME,
                    "model": "tiny" # Use tiny for faster verification
                }
            }
        }
        process.stdin.write(json.dumps(call_req) + "\n")
        process.stdin.flush()

        # Read tool response (this will block until transcription is done)
        print("Waiting for response (this may take a few minutes)...")
        response = process.stdout.readline()
        print(f"<<< Received: {response.strip()}")
        
        # Verify result
        try:
            res_json = json.loads(response)
            if "error" in res_json:
                print(f"!!! Error in response: {res_json['error']}")
            else:
                print("!!! Success response received.")
                content = res_json.get("result", {}).get("content", [])
                if content:
                    print(f"Result content preview: {str(content)[:200]}...")
                
                # Check file
                output_file = Path(OUTPUT_DIR) / f"{OUTPUT_NAME}.txt"
                if output_file.exists():
                     print(f"VERIFICATION: Output file exists at {output_file}")
                else:
                     print(f"VERIFICATION FAILED: Output file missing at {output_file}")

        except json.JSONDecodeError:
            print("!!! Failed to decode JSON response")

    except Exception as e:
        print(f"Error during test: {e}")
    finally:
        print("\nClosing server...")
        process.terminate()
        process.wait()

if __name__ == "__main__":
    main()
