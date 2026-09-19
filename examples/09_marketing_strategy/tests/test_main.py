import importlib.util
import sys
from pathlib import Path

import yaml
from crewai import Agent


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = EXAMPLE_ROOT / "src"
MODULE_PATH = SRC_ROOT / "main.py"
sys.path.insert(0, str(SRC_ROOT))
SPEC = importlib.util.spec_from_file_location("example09_main", MODULE_PATH)
main_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main_module)


def test_preferences_default_to_openrouter_and_mock_fallback():
    config_path = EXAMPLE_ROOT / "config" / "preferences.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["llm"]["provider"] == "openrouter"
    assert config["llm"]["model"] == "google/gemini-2.5-flash-lite"
    assert config["comfyui"]["mcp_server"] == "comfyui-dgspark"
    assert config["comfyui"]["host"] == "127.0.0.1"
    assert config["comfyui"]["port"] == 11002
    assert config["comfyui"]["allow_mock_fallback"] is True


def test_get_env_file_path_points_to_repo_root():
    env_path = main_module.get_env_file_path()

    assert Path(env_path).as_posix().lower() == "f:/repositories/crewai-mcp-lab/.env"


def test_select_comfy_server_name_uses_mock_when_unreachable():
    preferences = {"comfyui": {"mcp_server": "comfyui", "allow_mock_fallback": True}}

    server_name = main_module.select_comfy_server_name(preferences, comfy_reachable=False)

    assert server_name == "comfyui-mock"


def test_select_comfy_server_name_uses_real_when_reachable():
    preferences = {"comfyui": {"mcp_server": "comfyui-dgspark", "allow_mock_fallback": True}}

    server_name = main_module.select_comfy_server_name(preferences, comfy_reachable=True)

    assert server_name == "comfyui-dgspark"


def test_get_mock_comfy_server_path_points_to_bundled_mock():
    mock_server_path = main_module.get_mock_comfy_server_path()

    assert Path(mock_server_path).as_posix().endswith("/examples/09_marketing_strategy/TEST/mock_comfy_server.py")


def test_get_comfy_endpoint_uses_preferences_values():
    preferences = {"comfyui": {"host": "127.0.0.1", "port": 11002}}

    host, port = main_module.get_comfy_endpoint(preferences)

    assert host == "127.0.0.1"
    assert port == 11002


def test_persist_task_output_writes_missing_or_empty_file(tmp_path):
    output_path = tmp_path / "research.md"
    output_path.write_text("", encoding="utf-8")

    class DummyOutput:
        raw = "fresh research"

    class DummyTask:
        output = DummyOutput()

    main_module.persist_task_output(DummyTask(), str(output_path))

    assert output_path.read_text(encoding="utf-8") == "fresh research"


def test_get_image_output_path_uses_png_file_in_outputs():
    preferences = {"outputs": {"dir": "outputs"}}

    image_path = main_module.get_image_output_path(preferences)

    assert Path(image_path).as_posix().endswith("/examples/09_marketing_strategy/outputs/generated_image.png")


def test_generate_campaign_image_uses_file_output_path():
    from tasks import MarketingTasks

    task = MarketingTasks().generate_campaign_image(
        Agent(role="Designer", goal="Create image", backstory="Test agent"),
        context=[],
        output_path="F:/tmp/generated_image.png",
    )

    assert "Output Path: 'F:/tmp/generated_image.png'" in task.description
