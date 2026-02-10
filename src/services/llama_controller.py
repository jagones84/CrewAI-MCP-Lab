import os
import time
import subprocess
import requests
import logging
import psutil
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class LlamaController:
    """
    Manages the local Llama.cpp server process.
    Handles starting, stopping, and verifying the server.
    """
    
    def __init__(self, config):
        """
        Initialize with config dictionary.
        Expected config structure:
        {
            "model": "model_filename.gguf",
            "base_url": "http://localhost:8080/v1",
            "executable_path": "path/to/llama-server.exe",
            "models_dir": "path/to/models_dir"
        }
        """
        self.config = config
        self.process = None
        self.model = config.get("model")
        self.base_url = config.get("base_url", "http://localhost:8080/v1")
        
        # Parse host and port from base_url
        parsed_url = urlparse(self.base_url)
        self.host = parsed_url.hostname or "127.0.0.1"
        self.port = parsed_url.port or 8080
        
        self.executable_path = config.get("executable_path")
        self.models_dir = config.get("models_dir")
        
    def check_server_status(self):
        """Check if server is running and responsive."""
        try:
            # Try to get health or models endpoint
            response = requests.get(f"{self.base_url.replace('/v1', '')}/health", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        
        try:
            # Fallback to models endpoint which is standard OpenAI
            response = requests.get(f"{self.base_url}/models", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
            
        return False

    def kill_existing_process(self):
        """Kill any process listening on the configured port."""
        print(f"🧹 Checking for processes on port {self.port}...")
        killed = False
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == self.port:
                        print(f"⚠️  Found process {proc.info['name']} (PID: {proc.info['pid']}) on port {self.port}. Killing...")
                        proc.kill()
                        proc.wait(timeout=5)
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if not killed:
            # Also try to kill by executable name if provided, just in case
            if self.executable_path:
                exe_name = os.path.basename(self.executable_path)
                for proc in psutil.process_iter(['pid', 'name']):
                    try:
                        if proc.info['name'] == exe_name:
                            print(f"⚠️  Found {exe_name} (PID: {proc.info['pid']}). Killing...")
                            proc.kill()
                            proc.wait(timeout=5)
                    except:
                        pass

    def start_server(self):
        """Start the Llama server with the configured model."""
        if not self.executable_path or not self.models_dir:
            print("❌ Cannot start Llama server: 'executable_path' or 'models_dir' missing in config.")
            return False
            
        model_path = os.path.join(self.models_dir, self.model)
        if not os.path.exists(model_path):
            print(f"❌ Model file not found: {model_path}")
            return False
            
        # First, ensure clean slate
        self.kill_existing_process()
        
        print(f"🚀 Starting Llama server from: {self.executable_path}")
        print(f"📦 Model: {self.model}")
        
        cmd = [
            self.executable_path,
            "-m", model_path,
            "--port", str(self.port),
            "--host", self.host,
            "--n-gpu-layers", "35", # Default good value for 24GB VRAM, can be configurable
            "--ctx-size", "8192",  # Reduced context window to prevent memory issues/timeouts
            "--parallel", "1"       # Reduced parallel requests to simplify debugging
        ]
        
        try:
            # Redirect output to a log file for debugging
            self.log_file = open('llama_server.log', 'w')
            self.process = subprocess.Popen(
                cmd, 
                stdout=self.log_file,
                stderr=subprocess.STDOUT
            )
            print("⏳ Waiting for server to initialize...")
            
            # Wait loop
            for _ in range(30):
                time.sleep(2)
                if self.check_server_status():
                    print("✅ Llama server started successfully.")
                    return True
                    
            print("❌ Timed out waiting for Llama server to start.")
            self.kill_existing_process()
            return False
        except Exception as e:
            print(f"❌ Failed to start Llama server: {e}")
            return False

    def ensure_server_running(self):
        """
        High-level method to ensure the correct server is running.
        1. Check if running
        2. If running, check if it's healthy
        3. If not running, start it
        """
        if self.check_server_status():
            print("✅ Llama server is already running.")
            return True
            
        return self.start_server()
