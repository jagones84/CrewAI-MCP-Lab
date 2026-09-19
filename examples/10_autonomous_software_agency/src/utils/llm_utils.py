import requests
import time

def unload_vram(base_url="http://localhost:11434"):
    """
    Unload all models from Ollama VRAM.
    """
    print("🧹 Unloading Ollama VRAM...")
    try:
        # Check running models
        response = requests.get(f"{base_url}/api/ps", timeout=2)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if not models:
                print("ℹ️  No models loaded.")
                return

            for m in models:
                model_name = m.get("name")
                print(f"🔻 Unloading {model_name}...")
                # Unload by setting keep_alive = 0
                # We use /api/generate for base models or /api/chat
                requests.post(f"{base_url}/api/chat", json={
                    "model": model_name,
                    "keep_alive": 0
                }, timeout=2)
            
            # Wait a bit
            time.sleep(1)
            print("✅ VRAM unloaded.")
        else:
            print(f"⚠️  Could not list models: {response.status_code}")
            
    except Exception as e:
        print(f"⚠️  Error unloading VRAM: {e}")
