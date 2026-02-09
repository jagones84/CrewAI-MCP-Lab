import os
import requests
import logging
import psutil
import subprocess
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class OllamaController:
    """
    Manages the Ollama server process.
    Handles starting (if local exe provided), checking status, and loading models.
    """
    
    def __init__(self, config):
        """
        Initialize with config dictionary.
        Expected config structure:
        {
            "model": "llama3",
            "base_url": "http://localhost:11434/v1",
            "executable_path": "path/to/ollama.exe" (optional)
        }
        """
        self.config = config
        self.model = config.get("model")
        self.base_url = config.get("base_url", "http://localhost:11434/v1")
        
        # Parse host and port from base_url
        parsed_url = urlparse(self.base_url)
        self.host = parsed_url.hostname or "127.0.0.1"
        self.port = parsed_url.port or 11434
        
        self.executable_path = config.get("executable_path")
        if self.executable_path:
            self.executable_path = os.path.expandvars(self.executable_path)
        
    def check_server_status(self):
        """Check if Ollama server is running and responsive."""
        try:
            # Ollama API check
            response = requests.get(f"http://{self.host}:{self.port}/api/tags", timeout=2)
            if response.status_code == 200:
                return True
        except:
            pass
        return False

    def kill_existing_process(self):
        """Kill any process listening on the configured port."""
        print(f"🧹 Checking for Ollama processes on port {self.port}...")
        killed = False
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                # Check by name first as Ollama might spawn children
                if proc.info['name'] and 'ollama' in proc.info['name'].lower():
                    print(f"⚠️  Found process {proc.info['name']} (PID: {proc.info['pid']}). Killing...")
                    proc.kill()
                    proc.wait(timeout=5)
                    killed = True
                    continue
                    
                for conn in proc.connections(kind='inet'):
                    if conn.laddr.port == self.port:
                        print(f"⚠️  Found process {proc.info['name']} (PID: {proc.info['pid']}) on port {self.port}. Killing...")
                        proc.kill()
                        proc.wait(timeout=5)
                        killed = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        if killed:
            print("✅ Ollama process terminated.")
        else:
            print("ℹ️  No existing Ollama process found.")

    def start_server(self):
        """Start the Ollama server."""
        if self.check_server_status():
            print("✅ Ollama server is already running.")
            return True

        if not self.executable_path:
            # Try to run 'ollama serve' from PATH
            print("ℹ️  'executable_path' not set. Trying 'ollama serve' from PATH...")
            try:
                subprocess.Popen(["ollama", "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                print("⏳ Waiting for Ollama to start...")
                # Wait loop
                import time
                for _ in range(10):
                    time.sleep(1)
                    if self.check_server_status():
                        print("✅ Ollama started successfully.")
                        return True
                print("❌ Timed out waiting for Ollama to start.")
                return False
            except FileNotFoundError:
                print("❌ 'ollama' not found in PATH. Please set 'executable_path' in config.")
                return False

        if not os.path.exists(self.executable_path):
            print(f"❌ Ollama executable not found: {self.executable_path}")
            return False
            
        print(f"🚀 Starting Ollama from: {self.executable_path}")
        # Assuming executable_path points to the app installer or the binary? 
        # On Windows, usually it's "ollama.exe serve" or just running the app.
        # If it's the CLI binary:
        cmd = [self.executable_path, "serve"]
        try:
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            
            # Wait loop
            import time
            for _ in range(10):
                time.sleep(1)
                if self.check_server_status():
                    print("✅ Ollama started successfully.")
                    return True
            print("❌ Timed out waiting for Ollama to start.")
            return False
        except Exception as e:
             print(f"❌ Failed to start Ollama: {e}")
             return False

    def load_model(self):
        """Ensure the requested model is loaded."""
        if not self.check_server_status():
            return False
            
        print(f"📥 Verifying/Loading model: {self.model}")
        try:
            # Check if model exists
            response = requests.get(f"http://{self.host}:{self.port}/api/tags")
            models = [m['name'] for m in response.json().get('models', [])]
            
            # Simple fuzzy match or exact match
            if self.model not in models and f"{self.model}:latest" not in models:
                 print(f"⚠️  Model '{self.model}' not found in Ollama library. Attempting pull...")
                 # Start pull (blocking or async? blocking for simplicity)
                 subprocess.run(["ollama", "pull", self.model], check=True)
            
            # Preload model by sending a small request or just keep_alive
            # Actually, CrewAI will load it on first request.
            # But we can force it to verify.
            print(f"✅ Model '{self.model}' is ready.")
            return True
        except Exception as e:
            print(f"❌ Failed to load model: {e}")
            return False
