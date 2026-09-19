import os
from pathlib import Path

import appdirs

from src.utils.crewai_runtime import configure_crewai_runtime


def test_configure_crewai_runtime_redirects_crewai_paths(tmp_path, monkeypatch):
    monkeypatch.delenv("HOME", raising=False)
    monkeypatch.delenv("USERPROFILE", raising=False)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("APPDATA", raising=False)

    configured = configure_crewai_runtime(tmp_path)

    runtime_root = Path(configured["runtime_root"])
    config_path = Path(configured["config_path"])
    localappdata = Path(configured["localappdata"])
    appdata = Path(configured["appdata"])
    home = Path(configured["home"])

    assert runtime_root.exists()
    assert config_path == runtime_root / "home" / ".config" / "crewai" / "settings.json"
    assert localappdata == runtime_root / "localappdata"
    assert appdata == runtime_root / "appdata"
    assert home == runtime_root / "home"
    assert os.environ["HOME"] == str(home)
    assert os.environ["USERPROFILE"] == str(home)
    assert os.environ["LOCALAPPDATA"] == str(localappdata)
    assert os.environ["APPDATA"] == str(appdata)
    assert appdirs.user_data_dir("book_writer", "CrewAI").startswith(str(localappdata))


def test_configure_crewai_runtime_disables_external_tracing(tmp_path, monkeypatch):
    monkeypatch.setenv("CREWAI_TRACING_ENABLED", "true")
    monkeypatch.setenv("AGENTOPS_API_KEY", "secret")
    monkeypatch.setenv("LITELLM_SUCCESS_CALLBACKS", "agentops")
    monkeypatch.setenv("LITELLM_FAILURE_CALLBACKS", "agentops")
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)

    configure_crewai_runtime(tmp_path)

    assert os.environ["CREWAI_TRACING_ENABLED"] == "false"
    assert os.environ["OTEL_SDK_DISABLED"] == "true"
    assert os.environ["LITELLM_SUCCESS_CALLBACKS"] == ""
    assert os.environ["LITELLM_FAILURE_CALLBACKS"] == ""
    assert "AGENTOPS_API_KEY" not in os.environ
