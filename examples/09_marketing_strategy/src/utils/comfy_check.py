import urllib.request
import logging

def check_comfyui_connection(host: str = "127.0.0.1", port: int = 8188) -> bool:
    """
    Checks if ComfyUI server is reachable.
    """
    url = f"http://{host}:{port}/"
    try:
        with urllib.request.urlopen(url, timeout=2) as response:
            return response.status == 200
    except Exception as e:
        return False
