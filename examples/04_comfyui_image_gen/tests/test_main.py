"""Regression tests for example 04 helpers and CLI bootstrap.

These tests focus on the parts of the example that have historically broken
across the repo:
- ``.env`` is loaded from the repo root, not the example folder.
- Mock ComfyUI server exposes the same tool surface as the live one.
- Configuration loader fails loudly on bad input.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = EXAMPLE_ROOT.parent.parent

# Make the example's own `src` directory importable without colliding with the
# repo-level `src` package (which contains `mcp_loader`).
EXAMPLE_SRC = EXAMPLE_ROOT / "src"
for path in (str(EXAMPLE_SRC), str(REPO_ROOT)):
    if path not in sys.path:
        sys.path.insert(0, path)


def _load_example_main():
    """Import ``src/main.py`` from the example folder, bypassing the repo package."""
    main_path = EXAMPLE_SRC / "main.py"
    spec = importlib.util.spec_from_file_location("example04_main", main_path)
    assert spec and spec.loader, f"Could not build import spec for {main_path}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


example_main = _load_example_main()
ConfigLoader = importlib.import_module("src.config.config").ConfigLoader


def test_get_env_file_path_points_to_repo_root() -> None:
    """``get_env_file_path`` must resolve to ``<repo>/.env`` (repo-level)."""
    expected = REPO_ROOT / ".env"
    actual = Path(example_main.get_env_file_path())
    assert actual == expected


def test_get_config_path_points_to_example_config() -> None:
    """``get_config_path`` must resolve to the example's ``preferences.yaml``."""
    assert example_main.get_config_path() == str(EXAMPLE_ROOT / "config" / "preferences.yaml")


def test_get_mock_server_path_exists() -> None:
    """Bundled mock ComfyUI server must live next to the example."""
    path = Path(example_main.get_mock_server_path())
    assert path.exists()
    assert path.name == "mock_comfy_server.py"


def test_resolve_output_path_absolute() -> None:
    """Absolute paths are returned untouched."""
    absolute = "C:/tmp/whatever.png"
    assert example_main.resolve_output_path(absolute) == absolute


def test_resolve_output_path_relative(tmp_path, monkeypatch) -> None:
    """Relative paths are resolved against the example root."""
    monkeypatch.setattr(example_main, "EXAMPLE_ROOT", str(tmp_path))
    resolved = example_main.resolve_output_path("outputs/foo.png")
    assert resolved == str(tmp_path / "outputs" / "foo.png")


def test_select_comfy_server_prefers_configured_when_reachable() -> None:
    """Live server wins when reachable and mock fallback is allowed."""
    name = example_main.select_comfy_server_name(
        configured_server="comfyui-dgspark",
        allow_mock=True,
        comfy_reachable=True,
    )
    assert name == "comfyui-dgspark"


def test_select_comfy_server_falls_back_to_mock() -> None:
    """Mock fallback is used only when allowed and endpoint is down."""
    name = example_main.select_comfy_server_name(
        configured_server="comfyui-dgspark",
        allow_mock=True,
        comfy_reachable=False,
    )
    assert name == "comfyui-mock"


def test_select_comfy_server_does_not_force_mock_when_disabled() -> None:
    """If the user opted out of mock fallback we keep the configured name."""
    name = example_main.select_comfy_server_name(
        configured_server="comfyui-dgspark",
        allow_mock=False,
        comfy_reachable=False,
    )
    assert name == "comfyui-dgspark"


def test_config_loader_rejects_missing_file(tmp_path) -> None:
    """Missing config file raises ``FileNotFoundError``."""
    missing = tmp_path / "nope.yaml"
    with pytest.raises(FileNotFoundError):
        ConfigLoader.load_config(str(missing))


def test_config_loader_rejects_empty_file(tmp_path) -> None:
    """Empty config file raises ``ValueError``."""
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(ValueError):
        ConfigLoader.load_config(str(empty))


def test_config_loader_rejects_non_mapping(tmp_path) -> None:
    """A scalar root is rejected with a clear message."""
    scalar = tmp_path / "scalar.yaml"
    scalar.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(ValueError):
        ConfigLoader.load_config(str(scalar))


def test_config_loader_loads_real_preferences() -> None:
    """The shipped ``preferences.yaml`` must be a valid mapping."""
    config = ConfigLoader.load_config(example_main.get_config_path())
    assert "llm" in config
    assert "comfyui" in config


def test_get_llm_normalizes_openrouter(monkeypatch) -> None:
    """OpenRouter configs get the ``openrouter/`` prefix and the API key is wired."""
    from src.utils import llm_factory

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(llm_factory, "load_dotenv", lambda *args, **kwargs: True)

    llm = llm_factory.get_llm(
        {
            "provider": "openrouter",
            "model": "google/gemini-2.0-flash-001",
            "temperature": 0.2,
        }
    )

    assert llm.model == "openrouter/google/gemini-2.5-flash-lite"
    assert os.environ["OPENROUTER_API_KEY"] == "test-key"


# ---------------------------------------------------------------------------
# Pipeline / full-task surface tests
# ---------------------------------------------------------------------------


def test_valid_pipelines_declared() -> None:
    """Only ``simple`` and ``full`` are supported pipeline modes."""
    assert set(example_main.VALID_PIPELINES) == {"simple", "full"}


def test_tools_for_pipeline_simple() -> None:
    """The simple pipeline only needs ``generate_image`` and ``list_workflows``."""
    tools = example_main.TOOLS_FOR_PIPELINE["simple"]
    assert "generate_image" in tools
    assert "list_workflows" in tools
    assert "modify_image" not in tools
    assert "upscale_image" not in tools
    assert "remove_background" not in tools


def test_tools_for_pipeline_full() -> None:
    """The full pipeline needs every ComfyUI tool the example exposes."""
    tools = set(example_main.TOOLS_FOR_PIPELINE["full"])
    assert {
        "generate_image",
        "modify_image",
        "upscale_image",
        "remove_background",
        "list_workflows",
    } <= tools


def test_expected_output_paths_simple(monkeypatch, tmp_path) -> None:
    """Simple pipeline returns exactly one absolute path under the example root."""
    monkeypatch.setattr(example_main, "EXAMPLE_ROOT", str(tmp_path))
    paths = example_main.expected_output_paths(
        pipeline="simple",
        run_cfg={},
        comfy_cfg={"output_path": "outputs/only_one.png"},
    )
    assert len(paths) == 1
    assert paths[0] == str(tmp_path / "outputs" / "only_one.png")


def test_expected_output_paths_full_default(monkeypatch, tmp_path) -> None:
    """Full pipeline returns generate/modify/upscale paths under the example outputs dir."""
    monkeypatch.setattr(example_main, "EXAMPLE_ROOT", str(tmp_path))
    paths = example_main.expected_output_paths(
        pipeline="full",
        run_cfg={},
        comfy_cfg={"output_path": "outputs/generated_image.png"},
    )
    assert len(paths) == 3
    assert paths[0] == str(tmp_path / "outputs" / "generated.png")
    assert paths[1] == str(tmp_path / "outputs" / "modified.png")
    assert paths[2] == str(tmp_path / "outputs" / "upscaled.png")


def test_expected_output_paths_full_with_remove_bg(monkeypatch, tmp_path) -> None:
    """Setting ``also_remove_background`` adds a fourth path for the no-bg copy."""
    monkeypatch.setattr(example_main, "EXAMPLE_ROOT", str(tmp_path))
    paths = example_main.expected_output_paths(
        pipeline="full",
        run_cfg={"also_remove_background": True},
        comfy_cfg={"output_path": "outputs/generated_image.png"},
    )
    assert len(paths) == 4
    assert paths[3] == str(tmp_path / "outputs" / "no_bg.png")


def test_build_full_pipeline_creates_four_tasks_with_remove_bg() -> None:
    """``build_full_pipeline`` returns 3 or 4 tasks depending on the flag."""
    from src.tasks import ImageGenTasks

    # We don't want to instantiate real ``crewai.Task`` objects in unit
    # tests (that would require a real ``Agent`` and ``LLM``). Patch the
    # individual task factories with counters instead.
    factory = ImageGenTasks()
    counts = {"generate": 0, "modify": 0, "upscale": 0, "remove_bg": 0}

    def fake_generate(*args, **kwargs):
        counts["generate"] += 1
        return f"generate:{kwargs.get('output_path')}"

    def fake_modify(*args, **kwargs):
        counts["modify"] += 1
        return f"modify:{kwargs.get('output_path')}"

    def fake_upscale(*args, **kwargs):
        counts["upscale"] += 1
        return f"upscale:{kwargs.get('output_path')}"

    def fake_remove_bg(*args, **kwargs):
        counts["remove_bg"] += 1
        return f"remove_bg:{kwargs.get('output_path')}"

    factory.generate_image = fake_generate  # type: ignore[method-assign]
    factory.modify_image = fake_modify  # type: ignore[method-assign]
    factory.upscale_image = fake_upscale  # type: ignore[method-assign]
    factory.remove_background = fake_remove_bg  # type: ignore[method-assign]

    tasks_three = factory.build_full_pipeline(
        agent=None,
        prompt="x",
        negative_prompt="",
        seed=1,
        workflow="image_perfectDeliberate_text_to_image_API.json",
        generated_path="/tmp/g.png",
        edit_prompt="y",
        denoise=0.5,
        modified_path="/tmp/m.png",
        upscale_model="4x-UltraSharp.pth",
        upscaled_path="/tmp/u.png",
        also_remove_background=False,
    )
    assert len(tasks_three) == 3
    assert counts == {"generate": 1, "modify": 1, "upscale": 1, "remove_bg": 0}

    tasks_four = factory.build_full_pipeline(
        agent=None,
        prompt="x",
        negative_prompt="",
        seed=1,
        workflow="image_perfectDeliberate_text_to_image_API.json",
        generated_path="/tmp/g.png",
        edit_prompt="y",
        denoise=0.5,
        modified_path="/tmp/m.png",
        upscale_model="4x-UltraSharp.pth",
        upscaled_path="/tmp/u.png",
        also_remove_background=True,
        bg_removed_path="/tmp/bg.png",
    )
    assert len(tasks_four) == 4
    assert counts == {"generate": 2, "modify": 2, "upscale": 2, "remove_bg": 1}


def test_build_full_pipeline_rejects_remove_bg_without_path() -> None:
    """Requesting bg removal without a path is a hard error, not a silent skip."""
    from src.tasks import ImageGenTasks

    factory = ImageGenTasks()
    with pytest.raises(ValueError):
        factory.build_full_pipeline(
            agent=None,
            prompt="x",
            negative_prompt="",
            seed=1,
            workflow="image_perfectDeliberate_text_to_image_API.json",
            generated_path="/tmp/g.png",
            edit_prompt="y",
            denoise=0.5,
            modified_path="/tmp/m.png",
            upscale_model="4x-UltraSharp.pth",
            upscaled_path="/tmp/u.png",
            also_remove_background=True,
            bg_removed_path=None,
        )


# ---------------------------------------------------------------------------
# Mock MCP server tool surface
# ---------------------------------------------------------------------------


def _load_mock_server_module():
    """Import the bundled mock ComfyUI server as a stand-alone module."""
    mock_path = EXAMPLE_ROOT / "TEST" / "mock_comfy_server.py"
    spec = importlib.util.spec_from_file_location("example04_mock_comfy", mock_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_mock_server_exposes_full_tool_surface() -> None:
    """The mock server must expose every tool the example may request.

    This guards against a regression where the production MCP server adds
    new tools but the mock doesn't, which would let tests silently drift
    from the real behaviour.
    """
    server = _load_mock_server_module()
    expected = {
        "list_workflows",
        "generate_image",
        "modify_image",
        "upscale_image",
        "remove_background",
    }
    exposed = {name for name in dir(server) if not name.startswith("_")}
    # FastMCP stores tools in ``mcp._tool_manager._tools`` in modern
    # versions; fall back to scanning if the private API moved.
    try:
        tool_manager_tools = server.mcp._tool_manager._tools  # type: ignore[attr-defined]
        exposed = exposed | set(tool_manager_tools.keys())
    except AttributeError:
        pass
    missing = expected - exposed
    assert not missing, f"Mock server missing tools: {sorted(missing)}"


def test_mock_server_writes_a_real_png(tmp_path) -> None:
    """``generate_image`` writes a non-empty PNG to the requested path."""
    server = _load_mock_server_module()
    out = tmp_path / "x.png"
    result = server.generate_image(
        workflow_name="image_perfectDeliberate_text_to_image_API.json",
        prompt="test",
        output_path=str(out),
    )
    assert out.exists()
    assert out.stat().st_size > 0
    assert out.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert "Generated and saved to" in result


# ---------------------------------------------------------------------------
# CrewAI runtime redirection (sandbox work-around)
# ---------------------------------------------------------------------------


def test_configure_crewai_runtime_redirects_paths(tmp_path, monkeypatch) -> None:
    """``configure_crewai_runtime`` must rewrite HOME / LOCALAPPDATA and appdirs.

    This is the regression test for the TRAE sandbox bug that crashes
    CrewAI on the first kickoff when the default
    ``%LOCALAPPDATA%\\CrewAI`` is restricted.
    """
    import importlib

    # Reload the module under test so it picks up the new env vars and
    # appdirs monkey-patch in a clean state.
    if "src.utils.crewai_runtime" in sys.modules:
        del sys.modules["src.utils.crewai_runtime"]
    runtime_mod = importlib.import_module("src.utils.crewai_runtime")

    runtime_root = tmp_path / "rt"
    paths = runtime_mod.configure_crewai_runtime(runtime_root)
    assert paths["runtime_root"] == str(runtime_root.resolve())
    assert os.environ["HOME"] == paths["home"]
    assert os.environ["USERPROFILE"] == paths["home"]
    assert os.environ["LOCALAPPDATA"] == paths["localappdata"]
    assert os.environ["APPDATA"] == paths["appdata"]
    assert os.environ["CREWAI_TRACING_ENABLED"] == "false"
    assert os.environ["OTEL_SDK_DISABLED"] == "true"

    # ``appdirs`` was monkey-patched to keep everything under our
    # workspace root, never under the real ``%LOCALAPPDATA%``.
    import appdirs

    resolved = appdirs.user_data_dir("CrewAI", "CrewAI")
    assert resolved.startswith(str(runtime_root.resolve())), resolved
    # The original (un-overridden) appdirs would have returned something
    # under the real ``%LOCALAPPDATA%``. Make sure we did not regress to
    # the system default. The sandbox restriction applies to the real
    # ``%LOCALAPPDATA%\\CrewAI``, not the workspace redirect.
    import tempfile
    real_local = tempfile.gettempdir()  # never matches the workspace root
    assert not resolved.startswith(real_local) or str(runtime_root.resolve()) in resolved

    # Calling it again with the same root must be idempotent.
    paths2 = runtime_mod.configure_crewai_runtime(runtime_root)
    assert paths2 == paths


# ---------------------------------------------------------------------------
# ComfyUI helpers (model pre-flight validation)
# ---------------------------------------------------------------------------


def test_validate_workflow_models_reports_missing_unet() -> None:
    """A workflow referencing an unknown UNET must produce a clear error."""
    import importlib.util

    # Load ``comfy_helpers.py`` as a stand-alone module (the repo-level
    # ``mcp_servers/comfyui-dgspark/`` directory is not a package).
    helpers_path = (
        EXAMPLE_ROOT.parent.parent
        / "mcp_servers"
        / "comfyui-dgspark"
        / "comfy_helpers.py"
    )
    spec = importlib.util.spec_from_file_location("comfy_helpers_dgspark", helpers_path)
    assert spec and spec.loader
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    helpers.COMFYUI_SERVER_ADDRESS = "127.0.0.1:1"  # unused here

    # Fake the /object_info response by monkey-patching the helper.
    fake_info = {
        "UNETLoader": {
            "input": {
                "required": {
                    "unet_name": [
                        ["qwen_image_2512_bf16.safetensors"]
                    ]
                }
            }
        }
    }

    def fake_get_object_info() -> dict:
        return fake_info

    helpers._get_object_info = fake_get_object_info  # type: ignore[attr-defined]

    workflow = {
        "37": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "this_model_does_not_exist.safetensors"},
        }
    }
    errors = helpers.validate_workflow_models(workflow)
    assert len(errors) == 1
    assert "this_model_does_not_exist.safetensors" in errors[0]
    assert "UNETLoader" in errors[0]


def test_validate_workflow_models_silent_when_model_installed() -> None:
    """A workflow whose models are all installed must produce no errors."""
    import importlib.util

    helpers_path = (
        EXAMPLE_ROOT.parent.parent
        / "mcp_servers"
        / "comfyui-dgspark"
        / "comfy_helpers.py"
    )
    spec = importlib.util.spec_from_file_location("comfy_helpers_dgspark_ok", helpers_path)
    assert spec and spec.loader
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    helpers.COMFYUI_SERVER_ADDRESS = "127.0.0.1:1"

    fake_info = {
        "UNETLoader": {
            "input": {"required": {"unet_name": [["qwen_image_2512_bf16.safetensors"]]}}
        }
    }
    helpers._get_object_info = lambda: fake_info  # type: ignore[attr-defined]

    workflow = {
        "37": {
            "class_type": "UNETLoader",
            "inputs": {"unet_name": "qwen_image_2512_bf16.safetensors"},
        }
    }
    assert helpers.validate_workflow_models(workflow) == []
