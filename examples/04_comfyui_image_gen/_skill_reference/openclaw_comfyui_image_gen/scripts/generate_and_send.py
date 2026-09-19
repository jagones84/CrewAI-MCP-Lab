#!/usr/bin/env python3
"""
ComfyUI image generation helper.
Automates submit -> wait -> resolve exact output -> copy to workspace -> print sendable path.
"""

import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request

COMFYUI_OUTPUT = "/home/jagones/ComfyUI/output"
WORKSPACE_DIR = "/home/jagones/.openclaw/workspace"
MCP_SERVER = "node /home/jagones/ComfyUI/comfyui-mcp/dist/index.js"
COMFYUI_URL = "http://127.0.0.1:8188"
MEDIA_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def run_mcporter(tool, args_dict, timeout=60):
    """Call an MCP tool via mcporter with stdio transport."""
    mcporter_bin = shutil.which("mcporter")
    if not mcporter_bin:
        return None
    args_json = json.dumps(args_dict)
    cmd = [
        mcporter_bin,
        "call",
        tool,
        "--stdio",
        MCP_SERVER,
        "--args",
        args_json,
        "--output",
        "json",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        print(f"Error calling {tool}: {stderr}", file=sys.stderr)
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Failed to parse {tool} response: {result.stdout}", file=sys.stderr)
        return None


def comfyui_request(path, data=None):
    """Call ComfyUI HTTP API directly."""
    url = f"{COMFYUI_URL}{path}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def list_output_images():
    """Return all current ComfyUI output images with mtimes."""
    files = []
    try:
        for entry in os.scandir(COMFYUI_OUTPUT):
            if entry.is_file() and entry.name.lower().endswith(MEDIA_EXTENSIONS):
                files.append((entry.path, entry.stat().st_mtime))
    except FileNotFoundError:
        print(f"Output directory not found: {COMFYUI_OUTPUT}", file=sys.stderr)
    except OSError as exc:
        print(f"Error listing output directory: {exc}", file=sys.stderr)
    files.sort(key=lambda item: item[1], reverse=True)
    return files


def check_queue_idle():
    """Return True when ComfyUI queue is empty."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{COMFYUI_URL}/queue"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode != 0:
            return False
        data = json.loads(result.stdout)
        running = len(data.get("queue_running", []))
        pending = len(data.get("queue_pending", []))
        return running == 0 and pending == 0
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Queue check error: {exc}", file=sys.stderr)
        return False


def sanitize_output_name(raw_name):
    """Keep output names inside the workspace and ensure an image extension exists."""
    name = os.path.basename(raw_name.strip()) if raw_name else "generated.png"
    if not name:
        name = "generated.png"
    if not name.lower().endswith(MEDIA_EXTENSIONS):
        name += ".png"
    return name


def resolve_image_from_result(result):
    """Resolve output path from get_image when available."""
    if not result or result.get("status") != "completed":
        return None
    images = result.get("images") or []
    if not images:
        return None
    filename = images[0].get("filename")
    if not filename:
        return None
    path = os.path.join(COMFYUI_OUTPUT, filename)
    return path if os.path.exists(path) else None


def find_newest_new_file(before_files, started_at):
    """Prefer a new file created by this run over a stale older output."""
    after_files = list_output_images()
    if not after_files:
        return None

    before_paths = {path for path, _mtime in before_files}
    for path, mtime in after_files:
        if path not in before_paths and mtime >= started_at - 1:
            return path

    for path, mtime in after_files:
        if mtime >= started_at - 1:
            return path

    return after_files[0][0]


def wait_for_completion(max_wait=300, poll_seconds=5):
    """Wait until ComfyUI queue goes idle."""
    print("Waiting for generation to complete...")
    waited = 0
    while waited < max_wait:
        if check_queue_idle():
            print("Generation complete!")
            return True
        time.sleep(poll_seconds)
        waited += poll_seconds
        if waited % 30 == 0:
            print(f"  ...still waiting ({waited}s)")
    return False


def build_http_workflow(prompt, width, height):
    """Return a known-good minimal workflow for direct HTTP fallback."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": int(time.time() * 1000) % 2147483647,
                "steps": 30,
                "cfg": 7.5,
                "sampler_name": "dpmpp_2m",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["5", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["8", 0],
            },
        },
        "5": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "perfectdeliberate_v60.safetensors"},
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["5", 1]},
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "lowres, bad anatomy, blurry, watermark, text, deformed, ugly, cartoon",
                "clip": ["5", 1],
            },
        },
        "8": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1},
        },
        "9": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["5", 2]},
        },
        "10": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "openclaw_gen", "images": ["9", 0]},
        },
    }


def submit_generation(prompt, width, height):
    """Submit a generation request via mcporter, with direct HTTP fallback."""
    result = run_mcporter(
        "generate_image",
        {
            "prompt": prompt,
            "width": width,
            "height": height,
        },
        timeout=30,
    )
    if result:
        return result, "mcporter"

    print("mcporter not available in PATH, falling back to ComfyUI HTTP API.")
    result = comfyui_request("/prompt", {"prompt": build_http_workflow(prompt, width, height)})
    return result, "http"


def resolve_image(prompt_id, before_files, started_at, transport):
    """Resolve source image path for the current generation."""
    if transport == "mcporter":
        print("Resolving output image...")
        get_image_result = run_mcporter("get_image", {"prompt_id": prompt_id}, timeout=30)
        source_path = resolve_image_from_result(get_image_result)
        if source_path:
            return source_path

    history = comfyui_request(f"/history/{prompt_id}")
    if history and prompt_id in history:
        outputs = history[prompt_id].get("outputs", {})
        for node_output in outputs.values():
            for image in node_output.get("images", []):
                candidate = os.path.join(
                    COMFYUI_OUTPUT,
                    image.get("subfolder", ""),
                    image.get("filename", ""),
                )
                candidate = candidate.rstrip("/")
                if candidate and os.path.exists(candidate):
                    return candidate

    return find_newest_new_file(before_files, started_at)


def main():
    if len(sys.argv) < 2:
        print("Usage: generate_and_send.py '<prompt>' [width] [height] [output_name]")
        sys.exit(1)

    prompt = sys.argv[1]
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    height = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    output_name = sanitize_output_name(sys.argv[4] if len(sys.argv) > 4 else "generated.png")

    before_files = list_output_images()
    started_at = time.time()

    print("Submitting generation request...")
    print(f"Prompt: {prompt}")
    print(f"Size: {width}x{height}")

    result, transport = submit_generation(prompt, width, height)
    if not result:
        print("Failed to submit generation request", file=sys.stderr)
        sys.exit(1)

    prompt_id = result.get("prompt_id")
    if not prompt_id:
        print(f"No prompt_id in response: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"Queued with ID: {prompt_id}")
    if not wait_for_completion():
        print("Timeout waiting for generation", file=sys.stderr)
        sys.exit(1)

    source_path = resolve_image(prompt_id, before_files, started_at, transport)

    if not source_path or not os.path.exists(source_path):
        print("Could not locate generated image", file=sys.stderr)
        sys.exit(1)

    dest_path = os.path.join(WORKSPACE_DIR, output_name)
    shutil.copy2(source_path, dest_path)

    print(f"SOURCE_IMAGE: {source_path}")
    print(f"WORKSPACE_IMAGE: {dest_path}")
    print(f"READY_TO_SEND: {dest_path}")


if __name__ == "__main__":
    main()
