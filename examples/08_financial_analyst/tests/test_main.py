import importlib.util
import os
import sys
from pathlib import Path

import yaml


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = EXAMPLE_ROOT / "src" / "main.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("example08_main", MODULE_PATH)
main_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main_module)


def test_preferences_default_to_openrouter_profile():
    config_path = EXAMPLE_ROOT / "config" / "preferences.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["llm"]["provider"] == "openrouter"
    assert config["llm"]["model"] == "google/gemini-2.5-flash-lite"


def test_get_llm_normalizes_openrouter_settings(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(main_module, "LLM", DummyLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    llm = main_module.get_llm(
        {
            "llm": {
                "provider": "openrouter",
                "model": "anthropic/claude-3.5-sonnet",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.2,
            }
        }
    )

    assert llm is not None
    assert captured["model"] == "openrouter/google/gemini-2.5-flash-lite"
    assert captured["api_key"] == "sk-or-test"
    assert captured["temperature"] == 0.2
    assert "OPENAI_API_BASE" not in os.environ


def test_get_llm_upgrades_stale_openrouter_model(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(main_module, "LLM", DummyLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)

    llm = main_module.get_llm(
        {
            "llm": {
                "provider": "openrouter",
                "model": "anthropic/claude-3.5-sonnet",
                "base_url": "https://openrouter.ai/api/v1",
                "temperature": 0.2,
            }
        }
    )

    assert llm is not None
    assert captured["model"] == "openrouter/google/gemini-2.5-flash-lite"


def test_get_env_file_path_points_to_repo_root():
    env_path = main_module.get_env_file_path()

    assert Path(env_path).as_posix().lower() == "f:/repositories/crewai-mcp-lab/.env"
