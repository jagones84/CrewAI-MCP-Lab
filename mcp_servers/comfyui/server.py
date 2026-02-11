import argparse
import json
import os
import time
import uuid
import websocket
import urllib.request
import urllib.parse
import subprocess
import signal
from mcp.server.fastmcp import FastMCP

# Configuration
COMFYUI_SERVER_ADDRESS = os.environ.get("COMFYUI_SERVER_ADDRESS", "127.0.0.1:8188")
SSH_TUNNEL_REMOTE = os.environ.get("SSH_TUNNEL_REMOTE")  # e.g., "user@remote-host"
SSH_TUNNEL_DEST = os.environ.get("SSH_TUNNEL_DEST", "localhost:8188")
CLIENT_ID = str(uuid.uuid4())
COMFYUI_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFYUI_OUTPUT_DIR = os.path.join(COMFYUI_ROOT, "ComfyUI", "output")
WORKFLOW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workflow_files")

# Create workflows directory if it doesn't exist
if not os.path.exists(WORKFLOW_DIR):
    os.makedirs(WORKFLOW_DIR)

# SSH Tunnel Management
ssh_process = None

def start_ssh_tunnel():
    global ssh_process, COMFYUI_SERVER_ADDRESS
    if not SSH_TUNNEL_REMOTE:
        return

    local_port = COMFYUI_SERVER_ADDRESS.split(':')[-1]
    # Command: ssh -L [local_port]:[remote_dest] -N [remote_host]
    cmd = ["ssh", "-L", f"{local_port}:{SSH_TUNNEL_DEST}", "-N", SSH_TUNNEL_REMOTE]
    
    try:
        # Avoid printing to stdout as it breaks MCP protocol
        # Use a log file or stderr if absolutely necessary
        ssh_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(2)
    except Exception:
        pass

def stop_ssh_tunnel():
    global ssh_process
    if ssh_process:
        ssh_process.terminate()
        ssh_process.wait()

# Initialize MCP Server
mcp = FastMCP("ComfyUI")

# Start tunnel if configured before server runs
start_ssh_tunnel()

# Register cleanup for the tunnel
# FastMCP doesn't have on_shutdown, but we can use a try/finally block or a separate thread
# For now, we will handle the process lifecycle within the script context


def queue_prompt(prompt):
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFYUI_SERVER_ADDRESS}/prompt", data=data)
    try:
        return json.loads(urllib.request.urlopen(req).read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"HTTP {e.code}: {e.reason} - {error_body}")

def get_image(filename, subfolder, folder_type):
    data = {"filename": filename, "subfolder": subfolder, "type": folder_type}
    url_values = urllib.parse.urlencode(data)
    with urllib.request.urlopen(f"http://{COMFYUI_SERVER_ADDRESS}/view?{url_values}") as response:
        return response.read()

def get_history(prompt_id):
    with urllib.request.urlopen(f"http://{COMFYUI_SERVER_ADDRESS}/history/{prompt_id}") as response:
        return json.loads(response.read())

def find_node_by_class(workflow, class_type):
    """Find the first node of a specific class type."""
    for node_id, node in workflow.items():
        if node.get("class_type") == class_type:
            return node_id, node
    return None, None

def find_inputs_by_open_slot(workflow, slot_name):
    """Find nodes that have a specific input slot name."""
    matches = []
    for node_id, node in workflow.items():
        if "inputs" in node and slot_name in node["inputs"]:
            matches.append((node_id, node))
    return matches

@mcp.tool()
def list_workflows() -> list[str]:
    """List available workflows in the configured workflows directory."""
    if not os.path.exists(WORKFLOW_DIR):
        return []
    return [f for f in os.listdir(WORKFLOW_DIR) if f.endswith(".json")]

@mcp.tool()
def generate_image(workflow_name: str, prompt: str, negative_prompt: str = "", seed: int = None, output_path: str = None) -> str:
    """
    Generate an image using a specific ComfyUI workflow (saved in API format).
    Refers to the workflow file by name (e.g., 'flux.json').
    Automatically attempts to inject the prompt into CLIPTextEncode nodes.
    
    If 'output_path' is provided, the generated image(s) will be copied to that directory.
    """
    workflow_path = os.path.join(WORKFLOW_DIR, workflow_name)
    if not os.path.exists(workflow_path):
        return f"Error: Workflow file '{workflow_name}' not found in {WORKFLOW_DIR}"

    try:
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)
    except Exception as e:
        return f"Error loading workflow: {str(e)}"

    # Heuristic for prompt injection
    # 1. Find all CLIPTextEncode nodes
    clip_nodes = []
    for node_id, node in workflow.items():
        if node.get("class_type") == "CLIPTextEncode" or node.get("class_type") == "CLIPTextEncodeFlux":
             clip_nodes.append((node_id, node))
    
    # Needs to be smarter: usually one is connected to positive, one to negative.
    # We can try to guess based on existing text or just assign first to positive, second to negative if available.
    
    # Simple heuristic: If "text" input contains "positive" or "prompt" vs "negative"
    # Or just simple order: First found is positive, second is negative
    
    positive_node = None
    negative_node = None

    for nid, node in clip_nodes:
        current_text = node.get("inputs", {}).get("text", "").lower()
        if "negative" in current_text:
            negative_node = (nid, node)
        else:
            if positive_node is None:
                positive_node = (nid, node)
            elif negative_node is None:
                # If we already have a positive and this doesn't look explicitly negative, 
                # but we need a negative, assign it. 
                # BUT, ComfyUI default workflows often put positive at bottom or top.
                pass
    
    # Fallback: if we didn't find specific negative, but have 2 nodes, assume 2nd is negative
    if positive_node and not negative_node and len(clip_nodes) >= 2:
        if clip_nodes[0] == positive_node:
            negative_node = clip_nodes[1]
        else:
            negative_node = clip_nodes[0]

    if positive_node:
        workflow[positive_node[0]]["inputs"]["text"] = prompt
    
    if negative_node and negative_prompt:
        workflow[negative_node[0]]["inputs"]["text"] = negative_prompt

    # Randomize Seed (find KSampler or similar)
    if seed is None:
        import random
        seed = random.randint(1, 1000000000000)
    
    for node_id, node in workflow.items():
        if "inputs" in node and "seed" in node["inputs"]:
            node["inputs"]["seed"] = seed
        if "inputs" in node and "noise_seed" in node["inputs"]:
            node["inputs"]["noise_seed"] = seed

    # Connect to WebSocket
    ws = websocket.WebSocket()
    try:
        ws.connect(f"ws://{COMFYUI_SERVER_ADDRESS}/ws?clientId={CLIENT_ID}")
    except Exception as e:
        return f"Error connecting to ComfyUI WebSocket: {str(e)}. Is ComfyUI running?"

    try:
        # Send prompt
        prompt_res = queue_prompt(workflow)
        prompt_id = prompt_res['prompt_id']
        
        # Listen for completion
        while True:
            out = ws.recv()
            if isinstance(out, str):
                message = json.loads(out)
                if message['type'] == 'executing':
                    data = message['data']
                    if data['node'] is None and data['prompt_id'] == prompt_id:
                        # Execution finished
                        break
        
        # Get history to find finding outputs
        history = get_history(prompt_id)
        prompt_history = history[prompt_id]
        
        outputs = prompt_history.get('outputs', {})
        results = []
        
        import shutil
        if output_path:
            # Check if output_path is intended as a directory
            if os.path.isdir(output_path) or (not os.path.splitext(output_path)[1]):
                # It's a directory
                if not os.path.exists(output_path):
                    os.makedirs(output_path, exist_ok=True)
                # We will append filename later in the loop
                target_is_dir = True
            else:
                # Treat output_path as a full file path
                output_dir = os.path.dirname(output_path)
                if output_dir and not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                target_is_dir = False

        for node_id, node_output in outputs.items():
            if 'images' in node_output:
                for image in node_output['images']:
                    fname = image['filename']
                    ftype = image['type']
                    subfolder = image['subfolder']
                    
                    # Original path in ComfyUI output (kept for local logging)
                    original_file_path = os.path.join(COMFYUI_OUTPUT_DIR, subfolder, fname)
                    
                    if output_path:
                        if target_is_dir:
                            dest_path = os.path.join(output_path, fname)
                            # Handle duplicates
                            if os.path.exists(dest_path):
                                base, ext = os.path.splitext(fname)
                                dest_path = os.path.join(output_path, f"{base}_{len(results)}{ext}")
                        else:
                            # If multiple images are generated, append index to avoid overwrite
                            # First image gets the exact output_path name
                            if len(results) > 0:
                                base, ext = os.path.splitext(output_path)
                                dest_path = f"{base}_{len(results)}{ext}"
                            else:
                                dest_path = output_path
                            
                        try:
                            # Download via API instead of local copy for remote compatibility
                            image_data = get_image(fname, subfolder, ftype)
                            with open(dest_path, "wb") as f:
                                f.write(image_data)
                            results.append(f"Generated and saved to: {dest_path}")
                        except Exception as e:
                            results.append(f"Generated: {fname} but FAILED to save to {dest_path}: {str(e)}")
                    else:
                        results.append(f"Generated: {fname} (available at {COMFYUI_SERVER_ADDRESS}/view?filename={fname}&subfolder={subfolder}&type={ftype})")
        
        return "\n".join(results) if results else "Workflow executed but no images found in output."

    except Exception as e:
        return f"Error executing workflow: {str(e)}"
    finally:
        ws.close()

if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        stop_ssh_tunnel()
