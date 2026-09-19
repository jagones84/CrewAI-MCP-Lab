"""Minimal mock ComfyUI MCP server used as a local fallback for example 04.

It mirrors the production ``comfyui-dgspark`` tool surface so the example
can be exercised end-to-end on machines without GPU/CUDA and during CI:

* ``list_workflows`` — return the known workflow file names.
* ``generate_image`` — text-to-image (existing).
* ``modify_image``   — img2img / image modification (new).
* ``upscale_image``  — upscale an existing image (new).
* ``remove_background`` — strip the background of an existing image (new).

Every tool writes a tiny 1x1 PNG to the requested ``output_path`` so the
example's success-detection logic (``file exists and non empty``) keeps
working without a real ComfyUI server behind the scenes.
"""

from __future__ import annotations

import base64
import os
import sys
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ComfyUI-Mock")

# 1x1 transparent PNG, valid for every image-capable viewer.
DUMMY_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR"
    b"\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\x86b\x00"
    b"\x00\x00\x00IEND\xaeB`\x82"
)

# A slightly different dummy (red pixel) for modify/upscale to make the
# output visually distinguishable when a user inspects ``outputs/``.
DUMMY_PNG_RED = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4nGP8z8DwHwAFBQIAX8jx0gAAAABJRU5ErkJggg=="
)

_KNOWN_WORKFLOWS = [
    "image_perfectDeliberate_text_to_image_API.json",
    "default_workflow.json",
    "img2img_workflow.json",
    "upscale_workflow.json",
    "remove_background_workflow.json",
]


def _resolve_target(output_path: str) -> str:
    """Mirror the production tool: file path or directory both supported."""
    target = output_path
    looks_like_dir = (
        os.path.isdir(target)
        or (not os.path.splitext(target)[1] and not target.endswith(".png"))
    )
    if looks_like_dir:
        os.makedirs(target, exist_ok=True)
        target = os.path.join(target, "mock_generated_image.png")
    else:
        parent = os.path.dirname(target)
        if parent:
            os.makedirs(parent, exist_ok=True)
    return target


def _write_dummy(target: str, payload: bytes) -> str:
    try:
        with open(target, "wb") as handle:
            handle.write(payload)
    except OSError as exc:
        return f"MOCK: failed to write {target}: {exc}"
    return f"Generated and saved to: {target}"


@mcp.tool()
def list_workflows() -> list[str]:
    """List the workflows this mock server can run."""
    return list(_KNOWN_WORKFLOWS)


@mcp.tool()
def generate_image(
    workflow_name: str,
    prompt: str,
    negative_prompt: str = "",
    seed: Optional[int] = None,
    output_path: Optional[str] = None,
) -> str:
    """Pretend to generate an image and write a 1x1 PNG to the requested path."""
    print(
        f"[MOCK] generate_image workflow={workflow_name!r} seed={seed!r} "
        f"prompt={prompt!r} neg={negative_prompt!r} -> {output_path!r}",
        file=sys.stderr,
    )
    if not output_path:
        return "MOCK: no output_path provided"
    return _write_dummy(_resolve_target(output_path), DUMMY_PNG)


@mcp.tool()
def modify_image(
    source_path: str,
    prompt: str,
    output_path: str,
    denoise: float = 0.55,
    negative_prompt: str = "",
    seed: Optional[int] = None,
    workflow_name: str = "img2img_workflow.json",
) -> str:
    """Pretend to run an img2img workflow and write a different 1x1 PNG."""
    print(
        f"[MOCK] modify_image src={source_path!r} workflow={workflow_name!r} "
        f"denoise={denoise!r} seed={seed!r} -> {output_path!r}",
        file=sys.stderr,
    )
    if not output_path:
        return "MOCK: no output_path provided"
    if not source_path or not os.path.exists(source_path):
        return f"MOCK: source image not found: {source_path}"
    return _write_dummy(_resolve_target(output_path), DUMMY_PNG_RED)


@mcp.tool()
def upscale_image(
    source_path: str,
    output_path: str,
    model_name: str = "4x-UltraSharp.pth",
    workflow_name: str = "upscale_workflow.json",
) -> str:
    """Pretend to upscale an image and write a slightly different PNG."""
    print(
        f"[MOCK] upscale_image src={source_path!r} model={model_name!r} "
        f"workflow={workflow_name!r} -> {output_path!r}",
        file=sys.stderr,
    )
    if not output_path:
        return "MOCK: no output_path provided"
    if not source_path or not os.path.exists(source_path):
        return f"MOCK: source image not found: {source_path}"
    return _write_dummy(_resolve_target(output_path), DUMMY_PNG_RED)


@mcp.tool()
def remove_background(
    source_path: str,
    output_path: str,
    model: str = "RMBG-2.0",
    process_res: int = 1024,
    workflow_name: str = "remove_background_workflow.json",
) -> str:
    """Pretend to remove the background and write a transparent PNG."""
    print(
        f"[MOCK] remove_background src={source_path!r} model={model!r} "
        f"-> {output_path!r}",
        file=sys.stderr,
    )
    if not output_path:
        return "MOCK: no output_path provided"
    if not source_path or not os.path.exists(source_path):
        return f"MOCK: source image not found: {source_path}"
    return _write_dummy(_resolve_target(output_path), DUMMY_PNG)


if __name__ == "__main__":
    mcp.run()
