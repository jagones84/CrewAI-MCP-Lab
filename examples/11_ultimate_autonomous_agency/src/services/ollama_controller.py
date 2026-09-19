import requests
import subprocess
import time
import os
import psutil

class OllamaController:
    def __init__(self, model_name: str = "mistral", host: str = "localhost", port: int = 11434):
        self.model_name = model_name
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"

    def check_server_status(self) -> bool:
        """Check if Ollama server is running."""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            return response.status_code == 200
        except requests.RequestException:
            return False

    def start_server(self):
        """Start the Ollama server if it's not running."""
        if self.check_server_status():
            print("Ollama server is already running.")
            return True

        print("Starting Ollama server...")
        try:
            # On Windows, ollama app is usually in the PATH
            subprocess.Popen(["ollama", "serve"], 
                             stdout=subprocess.DEVNULL, 
                             stderr=subprocess.DEVNULL,
                             creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            
            # Wait for server to start
            for _ in range(10):
                if self.check_server_status():
                    print("Ollama server started successfully.")
                    return True
                time.sleep(2)
            
            print("Failed to start Ollama server.")
            return False
        except Exception as e:
            print(f"Error starting Ollama server: {e}")
            return False

    def load_model(self):
        """Ensure the model is pulled and loaded."""
        print(f"Ensuring model {self.model_name} is available...")
        try:
            response = requests.post(f"{self.base_url}/api/pull", 
                                     json={"name": self.model_name, "stream": False},
                                     timeout=300)
            if response.status_code == 200:
                print(f"Model {self.model_name} is ready.")
                return True
        except Exception as e:
            print(f"Error pulling model: {e}")
        return False

    def unload_vram(self):
        """Unload all models from VRAM by setting keep_alive to 0."""
        print("Unloading models from VRAM...")
        try:
            # Get currently loaded models
            response = requests.get(f"{self.base_url}/api/ps", timeout=2)
            if response.status_code == 200:
                models = response.json().get("models", [])
                for m in models:
                    model_to_unload = m.get("name")
                    print(f"Unloading {model_to_unload}...")
                    requests.post(f"{self.base_url}/api/chat", json={
                        "model": model_to_unload,
                        "keep_alive": 0,
                        "messages": []
                    }, timeout=2)
                return True
        except Exception as e:
            print(f"Error unloading VRAM: {e}")
        return False

    def stop_server(self):
        """Kill the Ollama process (Windows specific implementation)."""
        print("Stopping Ollama server...")
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'ollama.exe' or proc.info['name'] == 'ollama':
                try:
                    proc.kill()
                    print("Ollama process killed.")
                except Exception as e:
                    print(f"Could not kill process: {e}")
        return True
