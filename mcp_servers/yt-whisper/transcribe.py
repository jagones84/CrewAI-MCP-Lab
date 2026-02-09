import os
import subprocess
import whisper
import argparse
import sys
import torch
import shutil
import time
from pathlib import Path

def run_transcription_workflow(youtube_url, output_audio, output_text, start_time="00:00:00", end_time=None, model_name="small", use_cuda=True, language=None, beam_size=1):
    """
    Executes the transcription workflow using optimized yt-dlp native downloading (threaded)
    to fetch native audio (m4a/opus) without conversion, followed by Whisper transcription.
    """
    # 0. Sanitize URL (remove backticks, leading/trailing spaces)
    youtube_url = youtube_url.strip().strip('`').strip()
    
    start_total = time.time()
    
    # Get yt-dlp path from venv or use module
    python_exe = sys.executable
    
    # Use python -m yt_dlp to ensure we use the installed package in the current environment
    # This avoids path issues and ensures we use the version we expect
    yt_dlp_cmd = [python_exe, "-m", "yt_dlp"]

    # Force .m4a extension if not specified (faster download and compatible with Whisper)
    if not output_audio.endswith(('.m4a', '.opus', '.mp3')):
        output_audio += ".m4a"

    # Define output_audio_base for -o template
    output_audio_base = os.path.splitext(output_audio)[0]

    # 1. Download optimized
    print(f"Downloading audio using yt-dlp (Native Threaded)...", file=sys.stderr, flush=True)
    
    # Construct download section string
    # Format: "*00:00:04-00:01:00"
    is_full_video = False
    if end_time:
        section_range = f"*{start_time}-{end_time}"
    elif start_time != "00:00:00":
        section_range = f"*{start_time}-inf"
    else:
        is_full_video = True
        section_range = None

    # Remove extension from output_audio for yt-dlp command to avoid double extension (e.g. .m4a.m4a)
    # output_audio_base is already defined above
    # output_audio_base = os.path.splitext(output_audio)[0]

    cmd = yt_dlp_cmd + [
        "--newline", # Ensure line-based output for real-time logging
        "--no-warnings",
        "--concurrent-fragments", "10",
        "--extractor-args", "youtube:player_client=android,web",
    ]
    
    if section_range:
        cmd.extend(["--download-sections", section_range, "--force-keyframes-at-cuts"])
        
    cmd.extend([
        "--format", "bestaudio/best", # Relaxed format constraint to avoid failures
        youtube_url,
        "-o", output_audio_base + ".%(ext)s" # Explicitly use template to control extension
    ])

    # Define cookie strategies
    cookie_strategies = []
    
    # Check for local cookies.txt in various locations
    possible_cookie_paths = [
        os.path.join(os.getcwd(), "cookies.txt"), # Current working directory
        os.path.join(os.path.dirname(__file__), "cookies.txt"), # Script directory
        os.path.join(os.path.dirname(__file__), "..", "cookies.txt"), # Parent directory
        "F:\\MCP\\AUDIO\\MCP\\cookies.txt" # Hardcoded project root
    ]
    
    found_cookies = False
    for cookie_path in possible_cookie_paths:
        if os.path.exists(cookie_path):
            print(f"Found cookies.txt at: {cookie_path}", file=sys.stderr)
            cookie_strategies.append(["--cookies", cookie_path])
            found_cookies = True
            break # Use the first one found
            
    # Always include fallback (no cookies)
    cookie_strategies.append([])
    
    if not found_cookies:
        print("Warning: 'cookies.txt' not found. Download may fail due to bot detection.", file=sys.stderr)
        print("Please export your YouTube cookies to 'F:\\MCP\\AUDIO\\MCP\\cookies.txt' using a browser extension.", file=sys.stderr)

    download_success = False
    
    for strategy in cookie_strategies:
        print(f"Attempting download with cookie strategy: {strategy if strategy else 'None'}...", file=sys.stderr, flush=True)
        
        current_cmd = list(cmd) # Copy base command
        if strategy:
            # Insert strategy args before the URL (which is at index -3 in original cmd list)
            # Original cmd ends with: ..., youtube_url, "-o", output_audio_template]
            # We want to insert before youtube_url
            insert_idx = current_cmd.index(youtube_url)
            for arg in reversed(strategy):
                current_cmd.insert(insert_idx, arg)
        
        # Run yt-dlp with real-time output logging
        print(f"Running command: {' '.join(current_cmd)}", file=sys.stderr, flush=True)
        
        try:
            print(f"Executing: {' '.join(current_cmd)}", file=sys.stderr, flush=True)
            process = subprocess.Popen(
                current_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL, # Prevent waiting for input
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                cwd=os.getcwd() # Ensure correct CWD
            )
            
            # Read stdout (which includes stderr) in real-time
            print(f"Waiting for yt-dlp output...", file=sys.stderr, flush=True)
            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line:
                    if process.poll() is not None:
                        break
                    continue
                line_str = line.strip()
                output_lines.append(line_str)
                print(f"[yt-dlp] {line_str}", file=sys.stderr, flush=True)
                    
            # Check for errors
            if process.returncode != 0:
                print(f"Process failed with return code {process.returncode}", file=sys.stderr, flush=True)
                raise subprocess.CalledProcessError(process.returncode, current_cmd, output="\n".join(output_lines))
                
            print("Download completed.", file=sys.stderr, flush=True)
            download_success = True
            break
        except subprocess.CalledProcessError as e:
            print(f"Download failed with strategy {strategy}. Error code: {e.returncode}", file=sys.stderr, flush=True)
            # Use e.output instead of e.stderr since we redirected stderr to stdout
            print(f"Error output: {e.output}", file=sys.stderr, flush=True)
            continue

    if not download_success:
        # Collect all error logs to provide more context
        error_msg = "All download strategies failed.\n"
        if 'output_lines' in locals():
            error_msg += f"Last error output:\n{'\n'.join(output_lines)}"
        raise RuntimeError(error_msg)

    # Locate the actual downloaded file (yt-dlp might have changed extension or used .part)
    # We prefer .m4a
    final_audio_path = output_audio
    if not os.path.exists(final_audio_path):
         # Try to find it
         base_name = os.path.basename(output_audio_base)
         parent_dir = os.path.dirname(output_audio_base)
         if not parent_dir:
             parent_dir = "."
         
         final_audio_path = None
         
         # 1. Check if the exact expected file exists (with extension replaced if needed)
         # yt-dlp might have used the requested extension
         if os.path.exists(output_audio):
             final_audio_path = output_audio
         else:
             # 2. Search for files starting with base_name and having valid audio extension
             possible_files = [f for f in os.listdir(parent_dir) if f.startswith(base_name)]
             valid_extensions = ('.m4a', '.opus', '.mp3', '.wav', '.webm', '.mp4')
             audio_files = [f for f in possible_files if f.lower().endswith(valid_extensions)]
             
             if audio_files:
                 # Sort by length to pick the most likely match (shortest usually means exact match + ext)
                 audio_files.sort(key=len)
                 final_audio_path = os.path.join(parent_dir, audio_files[0])
             elif possible_files:
                  # Fallback to whatever file was found, but warn/log
                  print(f"Warning: No standard audio file found. Found: {possible_files}", file=sys.stderr, flush=True)
                  final_audio_path = os.path.join(parent_dir, possible_files[0])

         if not final_audio_path or not os.path.exists(final_audio_path):
              raise RuntimeError(f"Could not locate downloaded file for {output_audio_base}")

    # 2. Transcribe using Whisper or Faster-Whisper
    device = "cuda" if use_cuda and torch.cuda.is_available() else "cpu"
    print(f"Transcribing {final_audio_path} using Whisper model '{model_name}' on device '{device}'...", file=sys.stderr, flush=True)
    
    model = None
    
    # Try using faster-whisper if available
    try:
        from faster_whisper import WhisperModel
        print("Using faster-whisper backend...", file=sys.stderr, flush=True)
        
        # Determine compute type based on device
        compute_type = "float16" if device == "cuda" else "int8"
        
        print(f"Loading faster-whisper model '{model_name}' (compute_type={compute_type})...", file=sys.stderr, flush=True)
        model = WhisperModel(model_name, device=device, compute_type=compute_type)
        
        print(f"Starting transcription (language={language if language else 'auto'}, beam_size={beam_size})...", file=sys.stderr, flush=True)
        segments, info = model.transcribe(final_audio_path, language=language, beam_size=beam_size)
        
        print(f"Detected language '{info.language}' with probability {info.language_probability}", file=sys.stderr, flush=True)
        
        # Accumulate segments with progress logging
        full_text = ""
        segment_count = 0
        for segment in segments:
            full_text += segment.text
            segment_count += 1
            if segment_count % 10 == 0:
                    print(f"Processed {segment_count} segments...", file=sys.stderr, flush=True)
        
        print(f"\nTotal segments processed: {segment_count}", file=sys.stderr, flush=True)
        
        print(f"Saving transcription to: {output_text}", file=sys.stderr, flush=True)
        with open(output_text, "w", encoding="utf-8") as f:
            f.write(full_text)
            
        print(f"Transcription saved successfully.", file=sys.stderr, flush=True)
        
        end_total = time.time()
        elapsed = end_total - start_total
        print(f"\n--- Workflow completed in {elapsed:.2f} seconds ---", file=sys.stderr, flush=True)
        
        return full_text
        
    except ImportError:
        print("faster-whisper not found, falling back to standard openai-whisper...", file=sys.stderr, flush=True)
        try:
            print(f"Loading Whisper model '{model_name}'...", file=sys.stderr, flush=True)
            model = whisper.load_model(model_name, device=device)
            
            print(f"Starting transcription (language={language if language else 'auto'})...", file=sys.stderr, flush=True)
            # If language is None, Whisper will auto-detect it
            result = model.transcribe(final_audio_path, language=language, verbose=False)
            
            print(f"Saving transcription to: {output_text}", file=sys.stderr, flush=True)
            with open(output_text, "w", encoding="utf-8") as f:
                f.write(result["text"])
            
            print(f"Transcription saved successfully.", file=sys.stderr, flush=True)
            
            end_total = time.time()
            elapsed = end_total - start_total
            print(f"\n--- Workflow completed in {elapsed:.2f} seconds ---", file=sys.stderr, flush=True)
            
            return result["text"]
        except Exception as e:
            print(f"Error in standard whisper transcription: {e}", file=sys.stderr, flush=True)
            raise e
            
    except Exception as e:
        print(f"Error in faster-whisper transcription: {e}", file=sys.stderr, flush=True)
        print("Falling back to standard openai-whisper...", file=sys.stderr, flush=True)
        # Fallback logic duplicated or we can structure this better, but for now simple fallback
        try:
            if model: 
                del model
                torch.cuda.empty_cache()
            
            print(f"Loading Whisper model '{model_name}'...", file=sys.stderr, flush=True)
            model = whisper.load_model(model_name, device=device)
            
            print(f"Starting transcription (language={language if language else 'auto'})...", file=sys.stderr, flush=True)
            result = model.transcribe(final_audio_path, language=language, verbose=False)
            
            print(f"Saving transcription to: {output_text}", file=sys.stderr, flush=True)
            with open(output_text, "w", encoding="utf-8") as f:
                f.write(result["text"])
            
            print(f"Transcription saved successfully.", file=sys.stderr, flush=True)
            
            end_total = time.time()
            elapsed = end_total - start_total
            print(f"\n--- Workflow completed in {elapsed:.2f} seconds ---", file=sys.stderr, flush=True)
            
            return result["text"]
        except Exception as e2:
             print(f"Error in fallback whisper transcription: {e2}", file=sys.stderr, flush=True)
             raise e2
             
    finally:
        if model is not None:
            print(f"Cleaning up GPU memory...", file=sys.stderr, flush=True)
            del model
            if device == "cuda":
                torch.cuda.empty_cache()
                import gc
                gc.collect()
            print(f"GPU memory cleanup completed.", file=sys.stderr, flush=True)

def main():
    parser = argparse.ArgumentParser(description="YouTube Transcription Workflow (Accelerated)")
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--output_audio", default="output.mp3", help="Output MP3 file path")
    parser.add_argument("--output_text", default="output.txt", help="Output transcription text file path")
    parser.add_argument("--start", default="00:00:00", help="Start time (HH:MM:SS)")
    parser.add_argument("--to", default=None, help="End time (HH:MM:SS). Optional.")
    parser.add_argument("--model", default="medium", choices=["tiny", "base", "small", "medium", "large"], help="Whisper model to use")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage even if CUDA is available")

    args = parser.parse_args()

    try:
        run_transcription_workflow(
            args.url, 
            args.output_audio, 
            args.output_text, 
            args.start, 
            args.to, 
            args.model,
            not args.cpu
        )
        print("Workflow completed successfully!")
    except Exception as e:
        print(f"Error during workflow: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
