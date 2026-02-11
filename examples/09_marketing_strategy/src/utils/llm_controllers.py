import os
import time
import subprocess
import requests
import logging
import psutil
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
        else:
             try:
                print(f"🚀 Starting Ollama from {self.executable_path}...")
                subprocess.Popen([self.executable_path, "serve"], creationflags=subprocess.CREATE_NEW_CONSOLE)
                print("⏳ Waiting for Ollama to start...")
                # Wait loop
                for _ in range(10):
                    time.sleep(1)
                    if self.check_server_status():
                        print("✅ Ollama started successfully.")
                        return True
                print("❌ Timed out waiting for Ollama to start.")
                return False
             except FileNotFoundError:
                print(f"❌ Executable not found at {self.executable_path}")
                return False

    def stop_server(self):
        """Stop the server (kill process)."""
        self.kill_existing_process()


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
        if killed:
             print("✅ LlamaCpp process terminated.")

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
        
        print(f"🚀 Starting Llama server with model: {self.model}")
        cmd = [
            self.executable_path,
            "-m", model_path,
            "--port", str(self.port),
            "--host", self.host,
            "-c", "4096", # Context size
            "--n-gpu-layers", "35" # GPU offload
        ]
        
        try:
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_CONSOLE)
            print("⏳ Waiting for Llama server to start...")
            
            for _ in range(30): # Wait up to 30s for model load
                time.sleep(1)
                if self.check_server_status():
                    print("✅ Llama server started successfully.")
                    return True
            
            print("❌ Timed out waiting for Llama server to start.")
            return False
        except FileNotFoundError:
             print(f"❌ Executable not found at {self.executable_path}")
             return False

    def stop_server(self):
        self.kill_existing_process()
