import os
import sys

import yaml


EXAMPLE_ROOT = os.path.dirname(os.path.dirname(__file__))
SRC_ROOT = os.path.join(EXAMPLE_ROOT, "src")

if SRC_ROOT not in sys.path:
    sys.path.append(SRC_ROOT)

import main  # noqa: E402
from agents import AgencyAgents  # noqa: E402
from tasks import FileSpec, ProjectPlan  # noqa: E402
from tools import FileTools, TestTools  # noqa: E402


def test_preferences_default_to_openrouter():
    config_path = os.path.join(EXAMPLE_ROOT, "config", "preferences.yaml")
    with open(config_path, "r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)

    assert config["llm"]["provider"] == "openrouter"
    assert config["llm"]["openrouter"]["model"] == "google/gemini-2.5-flash-lite"
    assert config["llm"]["manager"]["provider"] == "openrouter"
    assert config["llm"]["manager"]["model"] == "google/gemini-2.5-flash-lite"


def test_get_env_file_path_points_to_repo_root():
    env_path = main.get_env_file_path()

    expected_path = os.path.join("f:\\REPOSITORIES\\Crewai-mcp-lab", ".env")
    assert os.path.normcase(env_path) == os.path.normcase(expected_path)


def test_build_embedder_config_disables_default_ollama_memory():
    assert main.build_embedder_config({}) is None


def test_get_llm_normalizes_openrouter_settings(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")

    agent_factory = AgencyAgents.__new__(AgencyAgents)
    llm = agent_factory._get_llm(
        {
            "provider": "openrouter",
            "openrouter": {"model": "google/gemini-2.0-flash-001"},
        }
    )

    assert llm.model == "openrouter/google/gemini-2.5-flash-lite"


def test_run_workspace_validation_executes_pytest_in_workspace(tmp_path):
    (tmp_path / "hello.py").write_text("def greet():\n    return 'Hello Agency'\n", encoding="utf-8")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_hello.py").write_text(
        "from hello import greet\n\n\ndef test_greet():\n    assert greet() == 'Hello Agency'\n",
        encoding="utf-8",
    )

    result = main.run_workspace_validation(str(tmp_path))

    assert result.passed is True
    assert result.summary == "Tests passed"


def test_run_tests_uses_current_python(monkeypatch):
    captured = {}

    class CompletedProcess:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["cwd"] = kwargs.get("cwd")
        return CompletedProcess()

    monkeypatch.setattr("tools.subprocess.run", fake_run)

    raw_result = TestTools.run_tests.func(test_dir="tests", cwd="workspace")

    assert captured["command"] == f'"{sys.executable}" -m pytest tests'
    assert captured["cwd"] == "workspace"
    assert '"passed": true' in raw_result


def test_initialize_workspace_from_plan_creates_declared_files(tmp_path):
    plan = ProjectPlan(
        project_name="demo",
        architecture_overview="demo",
        files=[
            FileSpec(path="src/app.py", description="app", dependencies=[]),
            FileSpec(path="tests/test_app.py", description="tests", dependencies=[]),
        ],
        test_strategy="pytest",
        requirements_txt_content="requests\npytest\n",
    )

    main.initialize_workspace_from_plan(plan, str(tmp_path))

    assert (tmp_path / "src" / "app.py").exists()
    assert (tmp_path / "tests" / "test_app.py").exists()
    assert (tmp_path / "requirements.txt").read_text(encoding="utf-8") == "requests\npytest\n"


def test_persist_generated_files_keeps_output_inside_workspace(tmp_path):
    main.persist_generated_files(
        workspace_path=str(tmp_path),
        generated_files=[
            {"path": "src/app.py", "content": "print('ok')\n"},
            {"path": "..\\README.md", "content": "should stay inside workspace\n"},
        ],
    )

    assert (tmp_path / "src" / "app.py").read_text(encoding="utf-8") == "print('ok')\n"
    assert (tmp_path / "README.md").read_text(encoding="utf-8") == "should stay inside workspace\n"


def test_write_file_uses_workspace_root_for_relative_paths(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENCY_WORKSPACE_ROOT", str(tmp_path))

    FileTools.write_file.func("nested/generated.py", "print('sandboxed')\n")

    assert (tmp_path / "nested" / "generated.py").read_text(encoding="utf-8") == "print('sandboxed')\n"


def test_write_file_collapses_redundant_workspace_prefix(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENCY_WORKSPACE_ROOT", str(tmp_path))
    monkeypatch.setenv("AGENCY_WORKSPACE_PREFIX", os.path.join("outputs", "workspace"))

    FileTools.write_file.func(os.path.join("outputs", "workspace", "requirements.txt"), "pytest\n")

    assert (tmp_path / "requirements.txt").read_text(encoding="utf-8") == "pytest\n"


def test_senior_developer_uses_file_tools_only(monkeypatch):
    class FakeAgent:
        def __init__(self, **kwargs):
            self.tools = kwargs["tools"]

    monkeypatch.setattr("agents.Agent", FakeAgent)

    agent_factory = AgencyAgents.__new__(AgencyAgents)
    agent_factory.llm = object()
    agent_factory.file_tools = ["write", "read"]
    agent_factory.shell_tools = ["shell"]

    developer = AgencyAgents.senior_developer(agent_factory)

    assert developer.tools == ["write", "read"]


def test_validate_generated_tests_rejects_import_fallbacks(tmp_path):
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_bad.py").write_text(
        "try:\n"
        "    from src.hello import say_hello\n"
        "except ImportError:\n"
        "    def say_hello():\n"
        "        print('fake')\n",
        encoding="utf-8",
    )

    result = main.validate_generated_tests(str(tmp_path))

    assert result.passed is False
    assert "fallback import" in result.summary.lower()


def test_repair_workspace_common_issues_restores_requirements_and_missing_scraper_wrapper(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    scraper_path = src_dir / "scraper.py"
    scraper_path.write_text(
        "def fetch_news():\n"
        "    return '<html></html>'\n\n"
        "def parse_news(html_content):\n"
        "    return []\n",
        encoding="utf-8",
    )
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("", encoding="utf-8")

    plan = ProjectPlan(
        project_name="demo",
        architecture_overview="demo",
        files=[FileSpec(path="src/scraper.py", description="scraper", dependencies=["requests"])],
        test_strategy="pytest",
        requirements_txt_content="requests\nbeautifulsoup4\npytest\n",
    )
    test_result = main.TestResult(
        passed=False,
        summary="Tests failed",
        failed_tests=["tests/test_scraper.py::test_scrape_hacker_news_success"],
        error_log="ImportError: cannot import name 'scrape_hacker_news' from 'src.scraper'",
    )

    repaired = main.repair_workspace_common_issues(str(tmp_path), plan, test_result)

    assert repaired is True
    assert set(requirements_path.read_text(encoding="utf-8").splitlines()) == {
        "requests",
        "beautifulsoup4",
        "pytest",
    }
    scraper_text = scraper_path.read_text(encoding="utf-8")
    assert "def scrape_hacker_news():" in scraper_text
    assert "html = fetch_news()" in scraper_text
    assert "return parse_news(html) if html else []" in scraper_text


def test_repair_workspace_common_issues_builds_empty_scraper_and_infers_requirements(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    scraper_path = src_dir / "scraper.py"
    scraper_path.write_text("", encoding="utf-8")
    (tests_dir / "test_scraper.py").write_text(
        "import unittest\n"
        "import requests_mock\n"
        "from bs4 import BeautifulSoup\n"
        "from src.scraper import scrape_news\n",
        encoding="utf-8",
    )
    requirements_path = tmp_path / "requirements.txt"
    requirements_path.write_text("crewai\n", encoding="utf-8")

    plan = ProjectPlan(
        project_name="demo",
        architecture_overview="demo",
        files=[FileSpec(path="src/scraper.py", description="scraper", dependencies=["requests"])],
        test_strategy="pytest",
        requirements_txt_content="crewai\n",
    )
    test_result = main.TestResult(
        passed=False,
        summary="Tests failed",
        failed_tests=["tests/test_scraper.py"],
        error_log="ImportError: cannot import name 'scrape_news' from 'src.scraper'",
    )

    repaired = main.repair_workspace_common_issues(str(tmp_path), plan, test_result)

    assert repaired is True
    scraper_text = scraper_path.read_text(encoding="utf-8")
    assert "def scrape_news(" in scraper_text
    assert "requests.get" in scraper_text
    assert "BeautifulSoup" in scraper_text

    requirements_text = requirements_path.read_text(encoding="utf-8")
    assert "requests" in requirements_text
    assert "beautifulsoup4" in requirements_text
    assert "requests-mock" in requirements_text


def test_repair_workspace_common_issues_rewrites_broken_scraper_tests(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (src_dir / "scraper.py").write_text(
        "import requests\n"
        "from bs4 import BeautifulSoup\n"
        "import csv\n\n"
        "def fetch_hacker_news():\n"
        "    return '<html></html>'\n\n"
        "def parse_headlines(html_content):\n"
        "    return []\n\n"
        "def save_to_csv(data, filename='hn_news.csv'):\n"
        "    pass\n",
        encoding="utf-8",
    )
    (tests_dir / "test_scraper.py").write_text("", encoding="utf-8")
    (tests_dir / "test_scraper_integration.py").write_text(
        "import pytest\n\n@pytest.pytest.fixture\ndef cleanup_csv():\n    yield\n",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text("crewai\n", encoding="utf-8")

    plan = ProjectPlan(
        project_name="demo",
        architecture_overview="demo",
        files=[FileSpec(path="src/scraper.py", description="scraper", dependencies=["requests"])],
        test_strategy="pytest",
        requirements_txt_content="crewai\n",
    )
    test_result = main.TestResult(
        passed=False,
        summary="Tests failed",
        failed_tests=["tests/test_scraper.py", "tests/test_scraper_integration.py"],
        error_log="ImportError: cannot import name 'scrape_news' from 'src.scraper'",
    )

    repaired = main.repair_workspace_common_issues(str(tmp_path), plan, test_result)

    assert repaired is True
    scraper_text = (src_dir / "scraper.py").read_text(encoding="utf-8")
    assert "def scrape_news(" in scraper_text

    unit_text = (tests_dir / "test_scraper.py").read_text(encoding="utf-8")
    integration_text = (tests_dir / "test_scraper_integration.py").read_text(encoding="utf-8")
    assert "scrape_news" in unit_text
    assert "@pytest.pytest.fixture" not in integration_text
    assert "@pytest.fixture" in integration_text


def test_repair_workspace_common_issues_can_replace_inconsistent_scraper_suite(tmp_path):
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()

    (src_dir / "scraper.py").write_text("import requests\n", encoding="utf-8")
    (tests_dir / "test_scraper.py").write_text("broken test suite\n", encoding="utf-8")
    (tmp_path / "requirements.txt").write_text("crewai\n", encoding="utf-8")

    plan = ProjectPlan(
        project_name="demo",
        architecture_overview="demo",
        files=[FileSpec(path="src/scraper.py", description="scraper", dependencies=["requests"])],
        test_strategy="pytest",
        requirements_txt_content="crewai\n",
    )
    test_result = main.TestResult(
        passed=False,
        summary="Tests failed",
        failed_tests=["tests/test_scraper.py::test_parse_headlines_success"],
        error_log="FAILED tests/test_scraper.py::test_parse_headlines_success",
    )

    repaired = main.repair_workspace_common_issues(str(tmp_path), plan, test_result)

    assert repaired is True
    scraper_text = (src_dir / "scraper.py").read_text(encoding="utf-8")
    unit_text = (tests_dir / "test_scraper.py").read_text(encoding="utf-8")
    assert "def scrape_news(" in scraper_text
    assert "def parse_headlines(" in scraper_text
    assert "from src.scraper import fetch_html, parse_headlines, save_to_csv, scrape_news" in unit_text
