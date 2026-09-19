#!/usr/bin/env python3
"""
ComfyUI image upscaling helper.
Automates upload -> submit -> wait -> resolve exact output -> copy to workspace -> print sendable path.
"""

import json
import os
import shutil
import sys
import time
import urllib.request
import uuid

COMFYUI_OUTPUT = "/home/jagones/ComfyUI/output"
WORKSPACE_DIR = "/home/jagones/.openclaw/workspace"
COMFYUI_URL = "http://127.0.0.1:8188"
DEFAULT_MODEL = "4x-UltraSharp.pth"
MEDIA_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")


def sanitize_output_name(raw_name, source_path):
    """Keep output names inside the workspace and ensure an image extension exists."""
    if raw_name:
        name = os.path.basename(raw_name.strip())
    else:
        stem, _ext = os.path.splitext(os.path.basename(source_path))
        name = f"{stem}_upscaled.png"
    if not name:
        name = "upscaled.png"
    if not name.lower().endswith(MEDIA_EXTENSIONS):
        name += ".png"
    return name


def list_output_images():
    """Return all current ComfyUI output images with mtimes."""
    files = []
    try:
        for root, _dirs, filenames in os.walk(COMFYUI_OUTPUT):
            for filename in filenames:
                if not filename.lower().endswith(MEDIA_EXTENSIONS):
                    continue
                path = os.path.join(root, filename)
                try:
                    files.append((path, os.path.getmtime(path)))
                except OSError:
                    continue
    except FileNotFoundError:
        print(f"Output directory not found: {COMFYUI_OUTPUT}", file=sys.stderr)
    files.sort(key=lambda item: item[1], reverse=True)
    return files


def comfyui_json_request(path, data=None):
    """Call ComfyUI HTTP API with JSON payloads."""
    url = f"{COMFYUI_URL}{path}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"} if body is not None else {}
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST" if body is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    return json.loads(payload) if payload else None


def upload_image(source_path):
    """Upload a local image into ComfyUI's input storage."""
    boundary = f"----OpenClawBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(source_path)

    with open(source_path, "rb") as handle:
        file_bytes = handle.read()

    lines = []
    lines.append(f"--{boundary}\r\n".encode("utf-8"))
    lines.append(
        f'Content-Disposition: form-data; name="image"; filename="{filename}"\r\n'.encode("utf-8")
    )
    lines.append(b"Content-Type: application/octet-stream\r\n\r\n")
    lines.append(file_bytes)
    lines.append(b"\r\n")
    lines.append(f"--{boundary}--\r\n".encode("utf-8"))
    body = b"".join(lines)

    request = urllib.request.Request(
        f"{COMFYUI_URL}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        payload = response.read()

    result = json.loads(payload.decode("utf-8"))
    uploaded_name = result.get("name")
    if not uploaded_name:
        raise RuntimeError(f"Upload did not return an image name: {result}")
    return uploaded_name


def check_queue_idle():
    """Return True when ComfyUI queue is empty."""
    try:
        data = comfyui_json_request("/queue")
        running = len(data.get("queue_running", []))
        pending = len(data.get("queue_pending", []))
        return running == 0 and pending == 0
    except Exception as exc:  # noqa: BLE001
        print(f"Queue check error: {exc}", file=sys.stderr)
        return False


def wait_for_completion(max_wait=600, poll_seconds=5):
    """Wait until ComfyUI queue goes idle."""
    print("Waiting for upscale to complete...")
    waited = 0
    while waited < max_wait:
        if check_queue_idle():
            print("Upscale complete!")
            return True
        time.sleep(poll_seconds)
        waited += poll_seconds
        if waited % 30 == 0:
            print(f"  ...still waiting ({waited}s)")
    return False


def build_upscale_workflow(uploaded_name, model_name, prefix):
    """Return a known-good minimal upscale workflow."""
    return {
        "1": {
            "class_type": "LoadImage",
            "inputs": {
                "image": uploaded_name,
                "upload": "image",
            },
        },
        "2": {
            "class_type": "UpscaleModelLoader",
            "inputs": {
                "model_name": model_name,
            },
        },
        "3": {
            "class_type": "ImageUpscaleWithModel",
            "inputs": {
                "upscale_model": ["2", 0],
                "image": ["1", 0],
            },
        },
        "4": {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": prefix,
                "images": ["3", 0],
            },
        },
    }


def resolve_image(prompt_id, before_files, started_at):
    """Resolve source image path for the current upscale run."""
    history = comfyui_json_request(f"/history/{prompt_id}")
    if history and prompt_id in history:
        outputs = history[prompt_id].get("outputs", {})
        for node_output in outputs.values():
            for image in node_output.get("images", []):
                candidate = os.path.join(
                    COMFYUI_OUTPUT,
                    image.get("subfolder", ""),
                    image.get("filename", ""),
                ).rstrip("/")
                if candidate and os.path.exists(candidate):
                    return candidate

    after_files = list_output_images()
    before_paths = {path for path, _mtime in before_files}
    for path, mtime in after_files:
        if path not in before_paths and mtime >= started_at - 1:
            return path
    for path, mtime in after_files:
        if mtime >= started_at - 1:
            return path
    return after_files[0][0] if after_files else None


def main():
    if len(sys.argv) < 2:
        print(
            "Usage: upscale_and_send.py /absolute/source/image [output_name] [upscale_model]",
            file=sys.stderr,
        )
        sys.exit(1)

    source_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(source_path):
        print(f"Source image not found: {source_path}", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(source_path):
        print(f"Source path is not a file: {source_path}", file=sys.stderr)
        sys.exit(1)

    output_name = sanitize_output_name(sys.argv[2] if len(sys.argv) > 2 else "", source_path)
    model_name = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_MODEL
    prefix = f"openclaw_upscale_{int(time.time())}"

    before_files = list_output_images()
    started_at = time.time()

    print("Uploading source image...")
    print(f"Source: {source_path}")
    print(f"Model: {model_name}")
    uploaded_name = upload_image(source_path)
    print(f"UPLOADED_IMAGE: {uploaded_name}")

    print("Submitting upscale request...")
    workflow = build_upscale_workflow(uploaded_name, model_name, prefix)
    result = comfyui_json_request(
        "/prompt",
        {
            "prompt": workflow,
            "client_id": f"openclaw-upscale-{uuid.uuid4().hex}",
        },
    )

    prompt_id = result.get("prompt_id") if result else None
    if not prompt_id:
        print(f"No prompt_id in response: {result}", file=sys.stderr)
        sys.exit(1)

    print(f"Queued with ID: {prompt_id}")
    if not wait_for_completion():
        print("Timeout waiting for upscale", file=sys.stderr)
        sys.exit(1)

    source_output_path = resolve_image(prompt_id, before_files, started_at)
    if not source_output_path or not os.path.exists(source_output_path):
        print("Could not locate upscaled image", file=sys.stderr)
        sys.exit(1)

    dest_path = os.path.join(WORKSPACE_DIR, output_name)
    shutil.copy2(source_output_path, dest_path)

    print(f"SOURCE_IMAGE: {source_output_path}")
    print(f"WORKSPACE_IMAGE: {dest_path}")
    print(f"READY_TO_SEND: {dest_path}")


if __name__ == "__main__":
    main()
