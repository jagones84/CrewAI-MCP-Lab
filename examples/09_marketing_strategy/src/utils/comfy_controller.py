import subprocess
import time
import os
import socket
import psutil
import sys

class ComfyController:
    def __init__(self, config: dict):
        """
        Initialize ComfyController.
        
        Args:
            config (dict): 'comfyui' section from preferences.yaml
        """
        self.config = config
        self.install_path = config.get("install_path")
        self.host = config.get("host", "127.0.0.1")
        self.port = config.get("port", 8188)
        self.python_path = config.get("python_path", sys.executable)
        self.process = None

    def check_server_status(self) -> bool:
        """Check if ComfyUI server is reachable."""
        try:
            with socket.create_connection((self.host, self.port), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError):
            return False

    def start_server(self) -> bool:
        """
        Start the ComfyUI server if not running.
        Returns True if server is running (started or already running).
        """
        if self.check_server_status():
            print(f"✅ ComfyUI is already running at {self.host}:{self.port}")
            return True

        if not self.install_path or not os.path.exists(self.install_path):
            print("⚠️ ComfyUI install_path not configured or invalid. Cannot auto-start.")
            print("Please configure 'comfyui.install_path' in preferences.yaml or start ComfyUI manually.")
            return False

        print(f"🚀 Starting ComfyUI from {self.install_path}...")
        
        main_py = os.path.join(self.install_path, "main.py")
        if not os.path.exists(main_py):
            print(f"❌ main.py not found in {self.install_path}")
            return False

        try:
            # Run in background
            # We use cwd=install_path because ComfyUI expects to run from its dir
            cmd = [self.python_path, "main.py", "--listen", self.host, "--port", str(self.port)]
            
            # If using windows portable, python might be different. 
            # But we assume user configured python_path if needed.
            
            self.process = subprocess.Popen(
                cmd,
                cwd=self.install_path,
                stdout=subprocess.DEVNULL, # Redirect to avoid cluttering console
                stderr=subprocess.DEVNULL, # Or maybe keep stderr for errors?
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # Wait for startup
            print("⏳ Waiting for ComfyUI to startup (this may take a moment)...")
            for _ in range(30): # Wait up to 30 seconds
                if self.check_server_status():
                    print("✅ ComfyUI started successfully!")
                    return True
                time.sleep(1)
            
            print("❌ Timed out waiting for ComfyUI to start.")
            return False
            
        except Exception as e:
            print(f"❌ Failed to start ComfyUI: {e}")
            return False

    def stop_server(self):
        """Stop the ComfyUI server if we started it."""
        if self.process:
            print("🛑 Stopping ComfyUI server...")
            try:
                parent = psutil.Process(self.process.pid)
                for child in parent.children(recursive=True):
                    child.terminate()
                parent.terminate()
                self.process.wait(timeout=5)
            except Exception as e:
                print(f"Error stopping ComfyUI: {e}")
            finally:
                self.process = None
