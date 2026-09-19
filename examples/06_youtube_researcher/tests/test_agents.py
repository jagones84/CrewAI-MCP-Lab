import importlib.util
import os
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "agents.py"
SPEC = importlib.util.spec_from_file_location("example06_agents", MODULE_PATH)
agents_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(agents_module)


def test_openrouter_model_uses_openrouter_prefix(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(agents_module, "LLM", DummyLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    agents_module.YoutubeResearcherAgents()

    assert captured["model"].startswith("openrouter/")
    assert os.environ["OPENROUTER_API_KEY"] == "sk-or-test"
    assert "OPENAI_API_BASE" not in os.environ


def test_stale_openrouter_model_is_upgraded(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(agents_module, "LLM", DummyLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)

    agents_module.YoutubeResearcherAgents()

    assert captured["model"] == "openrouter/google/gemini-2.5-flash-lite"
