import os
import sys
from pathlib import Path
from types import SimpleNamespace


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
if str(EXAMPLE_ROOT) not in sys.path:
    sys.path.insert(0, str(EXAMPLE_ROOT))

from src import main
from src import tools
from src import utils


def test_run_pytest_uses_current_python(monkeypatch, tmp_path):
    outputs_test_dir = tmp_path / "outputs" / "TEST"
    outputs_test_dir.mkdir(parents=True)

    captured = {}

    def fake_run(command, cwd, capture_output, text):
        captured["command"] = command
        captured["cwd"] = cwd
        return SimpleNamespace(returncode=0, stdout="1 passed", stderr="")

    monkeypatch.setattr(main, "EXAMPLE_ROOT", str(tmp_path))
    monkeypatch.setattr(main.subprocess, "run", fake_run)

    report = main.run_pytest("outputs/TEST")

    assert report["passed"] is True
    assert captured["command"][:3] == [sys.executable, "-m", "pytest"]
    assert os.path.normpath(captured["command"][3]) == os.path.normpath(str(outputs_test_dir))
    assert captured["cwd"] == str(tmp_path)


def test_testtools_run_tests_uses_current_python(monkeypatch, tmp_path):
    outputs_test_dir = tmp_path / "outputs" / "TEST"
    outputs_test_dir.mkdir(parents=True)

    captured = {}

    def fake_run(command, cwd, capture_output, text):
        captured["command"] = command
        captured["cwd"] = cwd
        return SimpleNamespace(returncode=0, stdout="1 passed", stderr="")

    monkeypatch.setattr(tools, "EXAMPLE_ROOT", str(tmp_path))
    monkeypatch.setattr(tools.subprocess, "run", fake_run)

    report = tools.run_pytest_command("outputs/TEST")

    assert '"passed": true' in report.lower()
    assert captured["command"][:3] == [sys.executable, "-m", "pytest"]
    assert os.path.normpath(captured["command"][3]) == os.path.normpath(str(outputs_test_dir))
    assert captured["cwd"] == str(tmp_path)


def test_ensure_minimum_artifacts_rewrites_invalid_generated_code(monkeypatch, tmp_path):
    src_dir = tmp_path / "outputs" / "src"
    test_dir = tmp_path / "outputs" / "TEST"
    src_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)

    (src_dir / "github_trending.py").write_text(
        "\n".join(
            [
                "import requests",
                "",
                "def get_trending_repos(top_n: int = 3):",
                "    return []",
                "",
                "def save_repos_to_json(repos, output_path):",
                "    pass",
                "",
                "def _default_output_path():",
                "    return 'data/trending_repos.json'",
                "",
                "def main():",
                "    return 0",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "EXAMPLE_ROOT", str(tmp_path))

    main.ensure_minimum_artifacts()

    content = (src_dir / "github_trending.py").read_text(encoding="utf-8")
    assert "urllib.request" in content
    assert "outputs\", \"trending_repos.json" in content
    assert "def parse_trending_repos" in content
    assert "import requests" not in content


def test_ensure_minimum_artifacts_rewrites_invalid_generated_tests(monkeypatch, tmp_path):
    src_dir = tmp_path / "outputs" / "src"
    test_dir = tmp_path / "outputs" / "TEST"
    src_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)

    (src_dir / "github_trending.py").write_text(
        "\n".join(
            [
                "def get_trending_repos(top_n: int = 3):",
                "    return []",
                "",
                "def save_repos_to_json(repos, output_path):",
                "    pass",
                "",
                "def main():",
                "    return 0",
            ]
        ),
        encoding="utf-8",
    )
    (test_dir / "test_github_trending.py").write_text(
        "\n".join(
            [
                "from outputs.src.github_trending import get_trending_repos",
                "",
                "def test_wrong_signature():",
                "    get_trending_repos('Python')",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "EXAMPLE_ROOT", str(tmp_path))

    main.ensure_minimum_artifacts()

    content = (test_dir / "test_github_trending.py").read_text(encoding="utf-8")
    assert "sys.path.insert" in content
    assert "import github_trending" in content
    assert "monkeypatch.setattr(" in content
    assert "outputs.src.github_trending" not in content


def test_ensure_minimum_artifacts_rewrites_semantically_bad_generated_tests(monkeypatch, tmp_path):
    src_dir = tmp_path / "outputs" / "src"
    test_dir = tmp_path / "outputs" / "TEST"
    src_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)

    (src_dir / "github_trending.py").write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "import json",
                "import os",
                "import re",
                "import urllib.request",
                "from html import unescape",
                "from typing import Any",
                "",
                "def parse_trending_repos(html: str, top_n: int = 3) -> list[dict[str, Any]]:",
                "    return []",
                "",
                "def get_trending_repos(top_n: int = 3) -> list[dict[str, Any]]:",
                "    return []",
                "",
                "def save_repos_to_json(repos: list[dict[str, Any]], output_path: str) -> None:",
                "    pass",
                "",
                "def _default_output_path() -> str:",
                "    return os.path.join('outputs', 'trending_repos.json')",
                "",
                "def main() -> int:",
                "    save_repos_to_json(get_trending_repos(top_n=3), _default_output_path())",
                "    return 0",
            ]
        ),
        encoding="utf-8",
    )
    (test_dir / "test_github_trending.py").write_text(
        "\n".join(
            [
                "import pytest",
                "from unittest.mock import MagicMock",
                "try:",
                "    import github_trending",
                "except ImportError:",
                "    import sys",
                "    sys.path.insert(0, 'outputs/src')",
                "    import github_trending",
                "",
                "def test_main(monkeypatch):",
                "    monkeypatch.setattr(github_trending, 'get_trending_repos', lambda: [])",
                "    mock_save_func = MagicMock()",
                "    monkeypatch.setattr(github_trending, 'save_repos_to_json', mock_save_func)",
                "    github_trending.main()",
                "    mock_save_func.assert_called_once()",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(main, "EXAMPLE_ROOT", str(tmp_path))

    main.ensure_minimum_artifacts()

    content = (test_dir / "test_github_trending.py").read_text(encoding="utf-8")
    assert "MagicMock()" not in content
    assert "except ImportError:" not in content
    assert "lambda top_n=3:" in content


def test_get_env_file_path_points_to_repo_root():
    assert os.path.normcase(os.path.normpath(main.get_env_file_path())) == os.path.normcase(os.path.normpath(
        "f:\\REPOSITORIES\\Crewai-mcp-lab\\.env"
    ))


def test_get_llm_normalizes_openrouter_settings(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.setattr(utils, "load_dotenv", lambda *args, **kwargs: True)

    monkeypatch.setattr(
        utils,
        "load_config",
        lambda: {
            "llm": {
                "provider": "openrouter",
                "model": "google/gemini-2.0-flash-001",
                "temperature": 0.1,
            }
        },
    )

    llm = utils.get_llm("llm")

    assert llm.model == "openrouter/google/gemini-2.5-flash-lite"
    assert os.environ["OPENROUTER_API_KEY"] == "test-key"
