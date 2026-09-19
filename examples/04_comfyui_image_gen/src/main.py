"""Example 04 entry point: ComfyUI image generation, modification, and upscaling.

This example demonstrates the ComfyUI MCP integration in two modes:

* ``pipeline: simple`` (default) — single text-to-image generation. Same
  behaviour as before; one agent, one task, one output PNG.
* ``pipeline: full``             — generate -> modify -> upscale, with an
  optional background-removal branch on the original image. The same
  visual-designer agent is reused, but receives the full MCP tool surface
  (``generate_image``, ``modify_image``, ``upscale_image``,
  ``remove_background``, ``list_workflows``) and runs an ordered list of
  tasks in a single :class:`crewai.Crew`.

The MCP server can be the production ``comfyui-dgspark`` (DGX Spark tunnel,
the same one used by example 05) or the bundled mock. The example falls
back to the mock only when ``allow_mock_fallback: true`` and the live
ComfyUI endpoint is not reachable.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from typing import Any, List

# ---------------------------------------------------------------------------
# IMPORTANT: redirect CrewAI runtime paths into a workspace-local directory
# BEFORE importing ``crewai``. The TRAE sandbox blocks writes to the default
# ``%LOCALAPPDATA%\\CrewAI`` location, which makes the crew crash on the
# first kickoff. This mirrors the same utility used in example 05.
# Loaded with importlib to avoid the repo-vs-example ``src/`` namespace
# collision.
# ---------------------------------------------------------------------------
import importlib.util

_CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
_EXAMPLE_ROOT = os.path.dirname(_CURRENT_DIR)
_REPO_ROOT = os.path.dirname(os.path.dirname(_EXAMPLE_ROOT))

_RUNTIME_UTIL_PATH = os.path.join(
    _EXAMPLE_ROOT, "src", "utils", "crewai_runtime.py"
)
_spec = importlib.util.spec_from_file_location(
    "crewai_runtime_local", _RUNTIME_UTIL_PATH
)
assert _spec and _spec.loader, f"Could not load crewai_runtime from {_RUNTIME_UTIL_PATH}"
_crewai_runtime = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_crewai_runtime)
configure_crewai_runtime = _crewai_runtime.configure_crewai_runtime

CURRENT_DIR = _CURRENT_DIR
EXAMPLE_ROOT = _EXAMPLE_ROOT
REPO_ROOT = _REPO_ROOT

# Make local imports work when running ``python src/main.py``.
sys.path.insert(0, EXAMPLE_ROOT)
sys.path.insert(0, CURRENT_DIR)

_RUNTIME_PATHS = configure_crewai_runtime(
    os.path.join(EXAMPLE_ROOT, "outputs", "_crewai_runtime")
)

from dotenv import load_dotenv  # noqa: E402
from mcp import StdioServerParameters  # noqa: E402
from crewai import Crew, Process  # noqa: E402
from crewai_tools import MCPServerAdapter  # noqa: E402

from src.agents import ImageGenAgents  # noqa: E402
from src.config.config import ConfigLoader  # noqa: E402
from src.tasks import ImageGenTasks  # noqa: E402
from src.utils.comfy_check import check_comfyui_connection  # noqa: E402
from src.utils.llm_factory import get_llm  # noqa: E402
from src.utils.logger import setup_logging  # noqa: E402

LOG_FILE = os.path.join(EXAMPLE_ROOT, "log", "log.txt")

VALID_PIPELINES = ("simple", "full")

# Tools required by each pipeline mode. The loader passes these names to
# the MCP adapter so the agent is only ever handed what it actually needs.
TOOLS_FOR_PIPELINE = {
    "simple": ["generate_image", "list_workflows"],
    "full": [
        "generate_image",
        "modify_image",
        "upscale_image",
        "remove_background",
        "list_workflows",
    ],
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Parsed arguments. ``pipeline`` is ``None`` unless explicitly
        provided, in which case the YAML value is overridden.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pipeline",
        choices=VALID_PIPELINES,
        default=None,
        help=(
            "Pipeline mode. 'simple' = single text-to-image. "
            "'full' = generate -> modify -> upscale (plus optional remove_background). "
            "If omitted, the YAML `run.pipeline` value is used."
        ),
    )
    return parser.parse_args()


def get_env_file_path() -> str:
    """Return the absolute path of the repository root ``.env`` file."""
    return os.path.join(REPO_ROOT, ".env")


def get_config_path() -> str:
    """Return the absolute path of the example ``preferences.yaml`` file."""
    return os.path.join(EXAMPLE_ROOT, "config", "preferences.yaml")


def get_mock_server_path() -> str:
    """Return the absolute path of the bundled mock ComfyUI MCP server."""
    return os.path.join(EXAMPLE_ROOT, "TEST", "mock_comfy_server.py")


def resolve_output_path(raw_path: str) -> str:
    """Resolve a possibly relative output path against the example root."""
    if os.path.isabs(raw_path):
        return raw_path
    return os.path.abspath(os.path.join(EXAMPLE_ROOT, raw_path))


def select_comfy_server_name(
    configured_server: str, allow_mock: bool, comfy_reachable: bool
) -> str:
    """Pick which ComfyUI MCP server name to load."""
    if comfy_reachable or not allow_mock:
        return configured_server
    return "comfyui-mock"


def build_mock_adapter() -> MCPServerAdapter:
    """Build an :class:`MCPServerAdapter` for the bundled mock ComfyUI server."""
    params = StdioServerParameters(
        command=sys.executable,
        args=[get_mock_server_path()],
        env=os.environ.copy(),
    )
    return MCPServerAdapter(params)


def build_repo_adapter(server_name: str, tool_names: List[str]) -> MCPServerAdapter:
    """Build an :class:`MCPServerAdapter` for a server declared in ``crewai_mcp.json``."""
    loader_path = os.path.join(REPO_ROOT, "src", "mcp_loader.py")
    if not os.path.exists(loader_path):
        raise FileNotFoundError(
            f"Repo-level MCPLoader not found at {loader_path}. "
            "Run this example from inside the Crewai-mcp-lab repository."
        )
    sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
    import importlib.util

    spec = importlib.util.spec_from_file_location("repo_mcp_loader", loader_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not build import spec for {loader_path}")
    loader_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loader_module)
    MCPLoader = loader_module.MCPLoader
    loader = MCPLoader(os.path.join(REPO_ROOT, "crewai_mcp.json"))
    return loader.load_server(server_name, tool_names=tool_names)


def persist_task_output(task: Any, output_path: str) -> None:
    """Persist the raw text output of a task to disk if the file is empty."""
    task_output = getattr(task, "output", None)
    raw_output = getattr(task_output, "raw", None) or ""
    if not raw_output:
        return
    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(raw_output)


def expected_output_paths(
    pipeline: str, run_cfg: dict[str, Any], comfy_cfg: dict[str, Any]
) -> List[str]:
    """Compute the absolute paths the example must produce.

    Args:
        pipeline: Either ``"simple"`` or ``"full"``.
        run_cfg: ``run`` section of the YAML config.
        comfy_cfg: ``comfyui`` section of the YAML config.

    Returns:
        List of absolute file paths. The example considers a run
        successful only if every file is present and non-empty.
    """
    if pipeline == "simple":
        return [resolve_output_path(
            run_cfg.get("output_path", comfy_cfg.get("output_path", "outputs/generated_image.png"))
        )]
    # full pipeline
    base_dir = os.path.dirname(
        resolve_output_path(
            run_cfg.get("output_path", comfy_cfg.get("output_path", "outputs/generated_image.png"))
        )
    ) or EXAMPLE_ROOT
    generated = resolve_output_path(
        run_cfg.get("generated_path", os.path.join(base_dir, "generated.png"))
    )
    modified = resolve_output_path(
        run_cfg.get("modified_path", os.path.join(base_dir, "modified.png"))
    )
    upscaled = resolve_output_path(
        run_cfg.get("upscaled_path", os.path.join(base_dir, "upscaled.png"))
    )
    paths = [generated, modified, upscaled]
    if run_cfg.get("also_remove_background", False):
        bg_removed = resolve_output_path(
            run_cfg.get("bg_removed_path", os.path.join(base_dir, "no_bg.png"))
        )
        paths.append(bg_removed)
    return paths


def run() -> int:
    """Execute the example end-to-end.

    Returns:
        Process exit code: ``0`` on success, non-zero on failure.
    """
    args = parse_args()
    logger = setup_logging(LOG_FILE)
    logger.info("Starting Example 04: ComfyUI Image Generation")

    load_dotenv(get_env_file_path(), override=True)

    try:
        config = ConfigLoader.load_config(get_config_path())
    except (FileNotFoundError, ValueError) as exc:
        logger.error("Failed to load preferences: %s", exc)
        return 1

    comfy_cfg = config.get("comfyui", {})
    run_cfg = config.get("run", {})

    pipeline = args.pipeline or run_cfg.get("pipeline", "simple")
    if pipeline not in VALID_PIPELINES:
        logger.error(
            "Invalid pipeline %r. Valid: %s", pipeline, ", ".join(VALID_PIPELINES)
        )
        return 1
    logger.info("Pipeline: %s", pipeline)

    configured_server = comfy_cfg.get("mcp_server", "comfyui-dgspark")
    allow_mock = bool(comfy_cfg.get("allow_mock_fallback", True))
    comfy_reachable = check_comfyui_connection(
        comfy_cfg.get("host", "127.0.0.1"),
        int(comfy_cfg.get("port", 11002)),
    )
    server_name = select_comfy_server_name(configured_server, allow_mock, comfy_reachable)
    if server_name == "comfyui-mock":
        logger.warning(
            "ComfyUI is not reachable. Falling back to the bundled mock server (allow_mock_fallback=true)."
        )
    else:
        logger.info("Using ComfyUI MCP server: %s (reachable=%s)", server_name, comfy_reachable)

    requested_tools = TOOLS_FOR_PIPELINE[pipeline]
    logger.info("Requested tool surface: %s", requested_tools)

    try:
        if server_name == "comfyui-mock":
            adapter = build_mock_adapter()
        else:
            adapter = build_repo_adapter(server_name, requested_tools)
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        logger.error("Failed to load ComfyUI MCP server %r: %s", server_name, exc)
        if allow_mock:
            logger.warning("Retrying with the bundled mock server.")
            adapter = build_mock_adapter()
            server_name = "comfyui-mock"
        else:
            return 1

    tools = list(getattr(adapter, "tools", []))
    if not tools:
        logger.error("No tools exposed by ComfyUI MCP server %r.", server_name)
        return 1
    tool_names_loaded = [t.name for t in tools]
    logger.info("Loaded %d ComfyUI tool(s): %s", len(tools), tool_names_loaded)

    # Hard check: the example should fail fast if the live MCP server is
    # missing a tool that the pipeline requires. The mock server always
    # implements the full surface, so this check is only strict for the
    # real server.
    if server_name != "comfyui-mock":
        missing = [name for name in requested_tools if name not in tool_names_loaded]
        if missing:
            logger.error(
                "ComfyUI MCP server %r is missing required tools: %s",
                server_name,
                missing,
            )
            return 1

    llm = get_llm(config.get("llm", {}))
    agents = ImageGenAgents(llm=llm)
    tasks = ImageGenTasks()

    designer = agents.visual_designer(tools)
    outputs = expected_output_paths(pipeline, run_cfg, comfy_cfg)
    for path in outputs:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if pipeline == "simple":
        simple_output = resolve_output_path(
            run_cfg.get("output_path", comfy_cfg.get("output_path", "outputs/generated_image.png"))
        )
        crew_tasks = [
            tasks.generate_image(
                agent=designer,
                prompt=run_cfg.get("prompt", "A neon-lit cyberpunk dragon over Tokyo at night, ultra detailed"),
                negative_prompt=run_cfg.get("negative_prompt", "blurry, low resolution, watermark"),
                seed=int(run_cfg.get("seed", 42)),
                workflow=comfy_cfg.get("workflow", "image_perfectDeliberate_text_to_image_API.json"),
                output_path=simple_output,
            )
        ]
    else:
        base_output = resolve_output_path(
            run_cfg.get("output_path", comfy_cfg.get("output_path", "outputs/generated_image.png"))
        )
        base_dir = os.path.dirname(base_output) or EXAMPLE_ROOT
        crew_tasks = tasks.build_full_pipeline(
            agent=designer,
            prompt=run_cfg.get("prompt", "A neon-lit cyberpunk dragon over Tokyo at night, ultra detailed"),
            negative_prompt=run_cfg.get("negative_prompt", "blurry, low resolution, watermark"),
            seed=int(run_cfg.get("seed", 42)),
            workflow=comfy_cfg.get("workflow", "image_perfectDeliberate_text_to_image_API.json"),
            generated_path=resolve_output_path(
                run_cfg.get("generated_path", os.path.join(base_dir, "generated.png"))
            ),
            edit_prompt=run_cfg.get(
                "edit_prompt",
                "Darker, more cinematic version with stronger rim lighting and a moodier palette.",
            ),
            denoise=float(run_cfg.get("denoise", 0.55)),
            modified_path=resolve_output_path(
                run_cfg.get("modified_path", os.path.join(base_dir, "modified.png"))
            ),
            upscale_model=run_cfg.get("upscale_model", "4x-UltraSharp.pth"),
            upscaled_path=resolve_output_path(
                run_cfg.get("upscaled_path", os.path.join(base_dir, "upscaled.png"))
            ),
            also_remove_background=bool(run_cfg.get("also_remove_background", False)),
            bg_removed_path=resolve_output_path(
                run_cfg.get("bg_removed_path", os.path.join(base_dir, "no_bg.png"))
            ),
        )

    crew = Crew(
        agents=[designer],
        tasks=crew_tasks,
        process=Process.sequential,
        verbose=True,
    )

    logger.info("Kicking off %s crew (%d task(s))...", pipeline, len(crew_tasks))
    started = datetime.now()
    try:
        result = crew.kickoff()
    except Exception as exc:  # noqa: BLE001
        logger.error("Crew failed: %s", exc)
        return 2
    elapsed = (datetime.now() - started).total_seconds()
    logger.info("Crew completed in %.1fs", elapsed)

    # Persist task raw text to a sibling log so the example folder always has proof.
    task_log_path = os.path.join(
        os.path.dirname(outputs[0]) or ".",
        "task_output.txt",
    )
    for t in crew_tasks:
        persist_task_output(t, task_log_path)

    print("######################")
    print(result)

    missing_outputs = [
        path
        for path in outputs
        if not (os.path.exists(path) and os.path.getsize(path) > 0)
    ]
    if missing_outputs:
        for path in missing_outputs:
            logger.error(
                "Pipeline %s finished but no file was produced at %s. "
                "Check that the corresponding ComfyUI tool received a file path (not a directory).",
                pipeline,
                path,
            )
        return 3

    for path in outputs:
        logger.info(
            "✅ %s ready: %s (%.1f KB)",
            pipeline,
            path,
            os.path.getsize(path) / 1024.0,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
