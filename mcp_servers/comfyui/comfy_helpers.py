"""Shared helpers used by the ComfyUI MCP servers.

This module centralises the few primitives that every ComfyUI tool needs:

* uploading a local image to ``/upload/image`` so that a workflow node can
  load it via ``LoadImage``;
* submitting a workflow JSON and waiting for completion through the
  ComfyUI WebSocket protocol;
* fetching the produced image bytes through the ``/view`` HTTP endpoint
  and writing them to a local file path.

The original `generate_image` tool still lives in
``comfy_dgspark_server.py`` for backwards compatibility with example 05;
``comfy_server.py`` (the local one) does the same. New tools
(``upscale_image``, ``remove_background``, ``modify_image``) reuse the
helpers defined here to keep the behaviour consistent.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Dict, Optional, Tuple

import websocket

# These globals are injected by the importing server module.
COMFYUI_SERVER_ADDRESS: str = "127.0.0.1:8188"
CLIENT_ID: str = str(uuid.uuid4())
WORKFLOW_DIR: str = ""
COMFYUI_OUTPUT_DIR: str = ""
DEBUG_LOG: str = ""


def _log(msg: str) -> None:
    """Append a line to the shared debug log if one is configured."""
    if not DEBUG_LOG:
        return
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%H:%M:%S')} - {msg}\n")
    except OSError:
        # Debug logging must never break a tool call.
        pass


def upload_image_to_comfyui(source_path: str, timeout: int = 120) -> str:
    """Upload ``source_path`` to ComfyUI's input directory.

    Returns the server-side filename (the one to plug into ``LoadImage``).
    Mirrors the multipart upload used by the openclaw ``comfyui-image-gen``
    skill so the behaviour is predictable.
    """
    if not os.path.isfile(source_path):
        raise FileNotFoundError(f"Source image not found: {source_path}")

    boundary = f"----ComfyuiMcpBoundary{uuid.uuid4().hex}"
    filename = os.path.basename(source_path)
    with open(source_path, "rb") as handle:
        file_bytes = handle.read()

    body = b"".join(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="image"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8"),
            b"Content-Type: application/octet-stream\r\n\r\n",
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )

    request = urllib.request.Request(
        f"http://{COMFYUI_SERVER_ADDRESS}/upload/image",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read()

    result = json.loads(payload.decode("utf-8"))
    uploaded_name = result.get("name")
    if not uploaded_name:
        raise RuntimeError(f"Upload did not return an image name: {result}")
    _log(f"Uploaded {source_path} as {uploaded_name}")
    return uploaded_name


def queue_prompt(workflow: Dict[str, Any]) -> Dict[str, Any]:
    """POST a workflow to ``/prompt`` and return the parsed response."""
    payload = {"prompt": workflow, "client_id": CLIENT_ID}
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"http://{COMFYUI_SERVER_ADDRESS}/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8")
        raise RuntimeError(
            f"ComfyUI API Error ({exc.code}): {error_body}"
        ) from exc


def get_history(prompt_id: str) -> Dict[str, Any]:
    """Return the parsed ``/history/{prompt_id}`` payload."""
    with urllib.request.urlopen(
        f"http://{COMFYUI_SERVER_ADDRESS}/history/{prompt_id}"
    ) as response:
        return json.loads(response.read())


def get_image_bytes(filename: str, subfolder: str, folder_type: str) -> bytes:
    """Fetch a ComfyUI image via the ``/view`` endpoint."""
    params = urllib.parse.urlencode(
        {"filename": filename, "subfolder": subfolder, "type": folder_type}
    )
    with urllib.request.urlopen(
        f"http://{COMFYUI_SERVER_ADDRESS}/view?{params}"
    ) as response:
        return response.read()


def wait_for_completion_via_ws(prompt_id: str, timeout: int = 600) -> None:
    """Block until the given ``prompt_id`` reports ``executing`` with ``node=None``.

    Uses a dedicated WebSocket client so we can be sure the same prompt id is
    the one we are waiting on (ComfyUI may run older prompts first).
    """
    ws = websocket.WebSocket()
    ws_url = f"ws://{COMFYUI_SERVER_ADDRESS}/ws?clientId={CLIENT_ID}"
    _log(f"Connecting to WebSocket: {ws_url}")
    try:
        ws.connect(ws_url)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Could not connect to ComfyUI WebSocket at {ws_url}: {exc}"
        ) from exc

    try:
        while True:
            try:
                ws.settimeout(timeout)
                out = ws.recv()
            except websocket.WebSocketTimeoutException as exc:
                raise RuntimeError(
                    f"WebSocket timed out after {timeout}s waiting for {prompt_id}"
                ) from exc
            if not isinstance(out, str):
                continue
            message = json.loads(out)
            if message.get("type") != "executing":
                continue
            data = message.get("data") or {}
            if data.get("prompt_id") != prompt_id:
                continue
            if data.get("node") is None:
                # Execution finished.
                return
    finally:
        try:
            ws.close()
        except Exception:  # noqa: BLE001
            pass


def find_first_output_image(prompt_id: str) -> Optional[Tuple[str, str, str]]:
    """Return the first image (``filename``, ``subfolder``, ``type``) for a prompt."""
    history = get_history(prompt_id)
    entry = history.get(prompt_id) or {}
    outputs = entry.get("outputs", {}) or {}
    for _node_id, node_output in outputs.items():
        for image in node_output.get("images", []) or []:
            filename = image.get("filename")
            if not filename:
                continue
            return filename, image.get("subfolder", ""), image.get("type", "output")
    return None


def run_workflow_to_file(
    workflow: Dict[str, Any],
    output_path: str,
    timeout: int = 600,
) -> str:
    """Submit a workflow, wait for completion, and save the first image to ``output_path``."""
    if not output_path:
        raise ValueError("output_path is required")

    out_dir = os.path.dirname(output_path)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir, exist_ok=True)

    response = queue_prompt(workflow)
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No prompt_id in ComfyUI response: {response}")
    _log(f"Queued prompt {prompt_id}")

    wait_for_completion_via_ws(prompt_id, timeout=timeout)

    image_info = find_first_output_image(prompt_id)
    if not image_info:
        raise RuntimeError(
            f"No image found in ComfyUI history for prompt {prompt_id}"
        )
    filename, subfolder, folder_type = image_info
    image_bytes = get_image_bytes(filename, subfolder, folder_type)
    with open(output_path, "wb") as handle:
        handle.write(image_bytes)
    _log(
        f"Saved {len(image_bytes)} bytes ({filename}) to {output_path} "
        f"via prompt {prompt_id}"
    )
    return output_path
