import argparse
import json
import os
import sys
import time
import uuid
import websocket
import urllib.request
import urllib.parse
import subprocess
import signal
import socket
from mcp.server.fastmcp import FastMCP

# Local shared helpers (upload / run / fetch).
import comfy_helpers

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

    local_port = int(COMFYUI_SERVER_ADDRESS.split(':')[-1])
    
    # Check if port is already in use
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', local_port))
    sock.close()
    
    if result == 0:
        log_debug(f"Port {local_port} is already in use. Assuming tunnel is already established externally.")
        return

    # Command: ssh -L [local_port]:[remote_dest] -N [remote_host]
    cmd = ["ssh", "-L", f"{local_port}:{SSH_TUNNEL_DEST}", "-N", SSH_TUNNEL_REMOTE]
    
    log_debug(f"Starting SSH tunnel: {' '.join(cmd)}")
    try:
        # Redirect stderr to a log file for debugging
        ssh_err_log = open(os.path.join(os.path.dirname(__file__), "ssh_error.log"), "w")
        # Ensure stdin is devnull to prevent ssh from hanging if it asks for input
        ssh_process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=ssh_err_log, stdin=subprocess.DEVNULL)
        time.sleep(5) # Give it more time to establish connection
        if ssh_process.poll() is not None:
             log_debug(f"SSH tunnel failed to start. Exit code: {ssh_process.returncode}")
        else:
             log_debug("SSH tunnel started successfully (or at least running)")
    except Exception as e:
        log_debug(f"SSH launch exception: {e}")
        pass

def stop_ssh_tunnel():
    global ssh_process
    if ssh_process:
        ssh_process.terminate()
        ssh_process.wait()

# Initialize MCP Server
mcp = FastMCP("ComfyUI")

DEBUG_LOG = os.path.join(os.path.dirname(__file__), "debug_log.txt")
def log_debug(msg):
    with open(DEBUG_LOG, "a") as f:
        f.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")

# Wire shared helpers to this server's globals.
comfy_helpers.COMFYUI_SERVER_ADDRESS = COMFYUI_SERVER_ADDRESS
comfy_helpers.CLIENT_ID = CLIENT_ID
comfy_helpers.WORKFLOW_DIR = WORKFLOW_DIR
comfy_helpers.COMFYUI_OUTPUT_DIR = COMFYUI_OUTPUT_DIR
comfy_helpers.DEBUG_LOG = DEBUG_LOG


# Start tunnel if configured before server runs
start_ssh_tunnel()

def queue_prompt(prompt):
    log_debug(f"Connecting to http://{COMFYUI_SERVER_ADDRESS}/prompt")
    p = {"prompt": prompt, "client_id": CLIENT_ID}
    data = json.dumps(p).encode('utf-8')
    req = urllib.request.Request(f"http://{COMFYUI_SERVER_ADDRESS}/prompt", data=data)
    try:
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        raise Exception(f"ComfyUI API Error ({e.code}): {error_body}")

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
    ws_url = f"ws://{COMFYUI_SERVER_ADDRESS}/ws?clientId={CLIENT_ID}"
    log_debug(f"Connecting to WebSocket: {ws_url}")
    try:
        ws.connect(ws_url)
    except Exception as e:
        log_debug(f"WebSocket connection failed: {e}")
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
            # Treat output_path as a full file path (not directory)
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)

        for node_id, node_output in outputs.items():
            if 'images' in node_output:
                for image in node_output['images']:
                    fname = image['filename']
                    ftype = image['type']
                    subfolder = image['subfolder']
                    
                    # Original path in ComfyUI output (kept for local logging)
                    original_file_path = os.path.join(COMFYUI_OUTPUT_DIR, subfolder, fname)
                    
                    if output_path:
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


# ---------------------------------------------------------------------------
# New tools: image post-processing (img2img, upscale, remove background).
# These mirror the canonical openclaw ``comfyui-image-gen`` skill. They upload
# a local image to ComfyUI, run a known-good workflow from ``workflow_files/``,
# then save the first produced image to ``output_path`` on the local machine.
# The original ``generate_image`` and ``list_workflows`` tools above are left
# untouched on purpose so example 05 keeps working unchanged.
# ---------------------------------------------------------------------------

def _load_workflow(workflow_name: str) -> dict:
    """Read a workflow JSON from the local ``workflow_files`` directory."""
    workflow_path = os.path.join(WORKFLOW_DIR, workflow_name)
    if not os.path.exists(workflow_path):
        raise FileNotFoundError(
            f"Workflow file '{workflow_name}' not found in {WORKFLOW_DIR}"
        )
    with open(workflow_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _find_first_node(workflow: dict, class_type: str):
    for node_id, node in workflow.items():
        if isinstance(node, dict) and node.get("class_type") == class_type:
            return node_id, node
    return None, None


def _sanitize_output_path(output_path: str) -> None:
    """Make sure the parent directory of ``output_path`` exists."""
    if not output_path:
        raise ValueError("output_path is required")
    parent = os.path.dirname(output_path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


@mcp.tool()
def upscale_image(
    source_path: str,
    output_path: str,
    model_name: str = "4x-UltraSharp.pth",
    workflow_name: str = "upscale_workflow.json",
) -> str:
    """Upscale ``source_path`` using a ComfyUI upscale model and save the result.

    Defaults:
        * workflow: ``upscale_workflow.json`` (LoadImage -> UpscaleModelLoader
          -> ImageUpscaleWithModel -> SaveImage).
        * model: ``4x-UltraSharp.pth``. ``RealESRGAN_x4plus.pth`` is also valid
          if installed on the ComfyUI side.

    The source image is uploaded to ComfyUI as ``image`` so the workflow's
    ``LoadImage`` node can pick it up. The first image in the resulting
    history entry is fetched and written to ``output_path``.
    """
    try:
        uploaded_name = comfy_helpers.upload_image_to_comfyui(source_path)
        workflow = _load_workflow(workflow_name)
        # Node 1 is LoadImage; node 2 is UpscaleModelLoader in our default
        # workflow. We patch by class to be tolerant of node id renumbering.
        _, load_node = _find_first_node(workflow, "LoadImage")
        if load_node is not None:
            load_node.setdefault("inputs", {})["image"] = uploaded_name
        _, model_node = _find_first_node(workflow, "UpscaleModelLoader")
        if model_node is not None:
            model_node.setdefault("inputs", {})["model_name"] = model_name
        # Fail fast with a clear error if a model is missing on the ComfyUI side.
        model_errors = comfy_helpers.validate_workflow_models(workflow)
        if model_errors:
            return "Error: " + " | ".join(model_errors)
        _sanitize_output_path(output_path)
        return (
            f"Upscaled and saved to: "
            f"{comfy_helpers.run_workflow_to_file(workflow, output_path)}"
        )
    except Exception as exc:  # noqa: BLE001
        return f"Error executing upscale: {exc}"


@mcp.tool()
def remove_background(
    source_path: str,
    output_path: str,
    model: str = "RMBG-2.0",
    process_res: int = 1024,
    workflow_name: str = "remove_background_workflow.json",
) -> str:
    """Remove the background from ``source_path`` and save the result as PNG.

    Uses the local ``remove_background_workflow.json`` (RMBG node). The
    default model name matches the value in the workflow JSON and can be
    overridden; the resolution hint is forwarded to the ``process_res``
    input of the RMBG node.
    """
    try:
        uploaded_name = comfy_helpers.upload_image_to_comfyui(source_path)
        workflow = _load_workflow(workflow_name)
        _, load_node = _find_first_node(workflow, "LoadImage")
        if load_node is not None:
            load_node.setdefault("inputs", {})["image"] = uploaded_name
        _, rmbg_node = _find_first_node(workflow, "RMBG")
        if rmbg_node is not None:
            inputs = rmbg_node.setdefault("inputs", {})
            if model:
                inputs["model"] = model
            if process_res:
                inputs["process_res"] = int(process_res)
        # ``validate_workflow_models`` only checks checkpoint-style loaders;
        # the RMBG custom node references its model by string, so the check
        # is a no-op here unless future loaders are added. We still call it
        # to keep the surface uniform.
        model_errors = comfy_helpers.validate_workflow_models(workflow)
        if model_errors:
            return "Error: " + " | ".join(model_errors)
        _sanitize_output_path(output_path)
        return (
            f"Background removed and saved to: "
            f"{comfy_helpers.run_workflow_to_file(workflow, output_path)}"
        )
    except Exception as exc:  # noqa: BLE001
        return f"Error executing remove_background: {exc}"


@mcp.tool()
def modify_image(
    source_path: str,
    prompt: str,
    output_path: str,
    denoise: float = 0.55,
    negative_prompt: str = "",
    seed: int = None,
    workflow_name: str = "img2img_workflow.json",
) -> str:
    """Modify an existing image via ComfyUI img2img and save the result.

    Uploads ``source_path`` to ComfyUI, runs an img2img workflow (default
    ``img2img_workflow.json``) with the provided prompt, denoise strength,
    optional negative prompt, and seed. Returns the saved file path.

    Denoise guidance:
        * ``0.25-0.45``: light edits, preserves the original.
        * ``0.5-0.7``:  normal restyle (default 0.55).
        * ``0.75+``:    strong transformation only when explicitly wanted.
    """
    try:
        denoise_f = float(denoise)
        if denoise_f < 0 or denoise_f > 1:
            return "Error: denoise must be between 0.0 and 1.0"
        uploaded_name = comfy_helpers.upload_image_to_comfyui(source_path)
        workflow = _load_workflow(workflow_name)
        # Inject uploaded filename into the first LoadImage node.
        _, load_node = _find_first_node(workflow, "LoadImage")
        if load_node is not None:
            load_node.setdefault("inputs", {})["image"] = uploaded_name
        # Inject prompt/negative into CLIPTextEncode nodes. The first node
        # without "negative" in its current text is treated as the positive
        # one; the second is the negative.
        clip_nodes = []
        for _nid, node in workflow.items():
            if (
                isinstance(node, dict)
                and node.get("class_type") in ("CLIPTextEncode", "CLIPTextEncodeFlux")
            ):
                clip_nodes.append((_nid, node))
        if clip_nodes:
            positive = clip_nodes[0]
            negative = clip_nodes[1] if len(clip_nodes) > 1 else None
            if negative is not None:
                current = (negative[1].get("inputs") or {}).get("text", "").lower()
                if "negative" not in current and "negative" in positive[1].get("inputs", {}).get("text", "").lower():
                    positive, negative = negative, positive
            positive[1].setdefault("inputs", {})["text"] = prompt
            if negative is not None:
                negative[1].setdefault("inputs", {})["text"] = (
                    negative_prompt or "lowres, bad anatomy, blurry, watermark, text, deformed, ugly, cartoon"
                )
        # Inject denoise + seed into the KSampler node.
        _, sampler_node = _find_first_node(workflow, "KSampler")
        if sampler_node is not None:
            inputs = sampler_node.setdefault("inputs", {})
            inputs["denoise"] = denoise_f
            if seed is not None:
                inputs["seed"] = int(seed)
            elif "seed" in inputs:
                import random
                inputs["seed"] = random.randint(1, 1000000000000)
        # Fail fast with a clear error if any model referenced by the
        # workflow is not installed on the ComfyUI side.
        model_errors = comfy_helpers.validate_workflow_models(workflow)
        if model_errors:
            return "Error: " + " | ".join(model_errors)
        _sanitize_output_path(output_path)
        return (
            f"Modified and saved to: "
            f"{comfy_helpers.run_workflow_to_file(workflow, output_path)}"
        )
    except Exception as exc:  # noqa: BLE001
        return f"Error executing modify_image: {exc}"


if __name__ == "__main__":
    try:
        mcp.run()
    finally:
        stop_ssh_tunnel()
