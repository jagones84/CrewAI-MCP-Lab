import importlib.util
import os
import sys
from pathlib import Path

import yaml


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = EXAMPLE_ROOT / "src" / "main.py"
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("example07_main", MODULE_PATH)
main_module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(main_module)


def test_preferences_default_to_openrouter_profile():
    config_path = EXAMPLE_ROOT / "config" / "preferences.yaml"
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    assert config["llm_config"]["selected"] == "openrouter"
    assert config["llm_config"]["profiles"]["openrouter"]["provider"] == "openrouter"


def test_get_llm_instance_normalizes_openrouter_settings(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(main_module, "LLM", DummyLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.5-flash-lite")
    monkeypatch.setenv("OPENAI_API_BASE", "https://openrouter.ai/api/v1")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    llm = main_module.get_llm_instance(
        {
            "llm_config": {
                "selected": "openrouter",
                "profiles": {
                    "openrouter": {
                        "provider": "openai",
                        "model": "anthropic/claude-3.5-sonnet",
                        "base_url": "https://openrouter.ai/api/v1",
                    }
                },
            }
        }
    )

    assert llm is not None
    assert captured["model"] == "openrouter/google/gemini-2.5-flash-lite"
    assert captured["api_key"] == "sk-or-test"
    assert "OPENAI_API_BASE" not in os.environ


def test_get_llm_instance_upgrades_stale_openrouter_model(monkeypatch):
    captured = {}

    class DummyLLM:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(main_module, "LLM", DummyLLM)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.setenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)

    llm = main_module.get_llm_instance(
        {
            "llm_config": {
                "selected": "openrouter",
                "profiles": {
                    "openrouter": {
                        "provider": "openrouter",
                        "model": "anthropic/claude-3.5-sonnet",
                        "base_url": "https://openrouter.ai/api/v1",
                    }
                },
            }
        }
    )

    assert llm is not None
    assert captured["model"] == "openrouter/google/gemini-2.5-flash-lite"


def test_extract_json_payload_reads_code_fenced_json():
    response = """
    Here is the shortlist:

    ```json
    [
      {"title": "Dune: Part Two", "year": 2024},
      {"title": "Godzilla Minus One", "year": 2023}
    ]
    ```
    """

    payload = main_module.extract_json_payload(response)

    assert payload[0]["title"] == "Dune: Part Two"
    assert payload[1]["year"] == 2023


def test_parse_justwatch_results_filters_matching_subscriptions():
    search_output = """
    Search results for 'Example' in US (2 result(s)):

    1.
    Title: Rebel Moon - Part One: A Child of Fire
      Entry ID: tm123
      Type: MOVIE
      Release Year: 2023
      IMDb Score: 5.6/10
      TMDb Score: 6.1/10
      Available on 3 platform(s):
        - Netflix (FLATRATE, _4K)
          URL: https://www.netflix.com/title/abc
        - Amazon Video (RENT, _4K, Price: $3.99)
          URL: https://www.amazon.com/example-rent

    2.
    Title: Dune: Part Two
      Entry ID: tm456
      Type: MOVIE
      Release Year: 2024
      IMDb Score: 8.4/10
      TMDb Score: 8.1/10
      Available on 2 platform(s):
        - HBO Max (FLATRATE, _4K)
          URL: https://play.hbomax.com/show/example
        - Apple TV Store (RENT, _4K, Price: $3.99)
          URL: https://tv.apple.com/example
    """

    matches = main_module.parse_justwatch_results(
        search_output,
        subscribed_providers=["Netflix", "Amazon Prime Video"],
        only_free_included=True,
    )

    assert len(matches) == 1
    assert matches[0]["title"] == "Rebel Moon - Part One: A Child of Fire"
    assert matches[0]["offers"] == [
        {"provider": "Netflix", "url": "https://www.netflix.com/title/abc"}
    ]


def test_render_markdown_report_outputs_table_and_editors_choice():
    report = main_module.render_markdown_report(
        [
            {
                "title": "Dune: Part Two",
                "type": "Movie",
                "year": 2024,
                "critic_score": "92%",
                "audience_score": "8.4/10",
                "vibe_match": "Epic sci-fi spectacle with overwhelming scale.",
                "streaming_options": [
                    {"provider": "Netflix", "url": "https://www.netflix.com/title/1"}
                ],
            },
            {
                "title": "Godzilla Minus One",
                "type": "Movie",
                "year": 2023,
                "critic_score": "98%",
                "audience_score": "8.3/10",
                "vibe_match": "Emotional and visually striking kaiju drama.",
                "streaming_options": [
                    {"provider": "Netflix", "url": "https://www.netflix.com/title/2"}
                ],
            },
        ]
    )

    assert "| Title | Type | Year | Critic Score | Audience Score | Vibe Match | Streaming Options |" in report
    assert "[Netflix](https://www.netflix.com/title/1)" in report
    assert "Editor's Choice" in report
    assert "Godzilla Minus One" in report


def test_movie_matches_criteria_rejects_wrong_type_year_and_score():
    criteria = {
        "year_range": "2023-2024",
        "content_type": "movie",
        "min_score": 7.5,
    }

    assert main_module.movie_matches_criteria(
        {"type": "Movie", "year": 2024, "imdb_score": "8.4/10", "tmdb_score": "8.1/10"},
        criteria,
    )
    assert not main_module.movie_matches_criteria(
        {"type": "Show", "year": 2024, "imdb_score": "8.4/10", "tmdb_score": "8.1/10"},
        criteria,
    )
    assert not main_module.movie_matches_criteria(
        {"type": "Movie", "year": 1989, "imdb_score": "8.4/10", "tmdb_score": "8.1/10"},
        criteria,
    )
    assert not main_module.movie_matches_criteria(
        {"type": "Movie", "year": 2024, "imdb_score": "6.0/10", "tmdb_score": "6.1/10"},
        criteria,
    )


def test_build_candidate_queries_returns_multiple_angles():
    criteria = {
        "year_range": "2023-2024",
        "genres": ["Sci-Fi", "Action", "Thriller", "Drama"],
        "content_type": "movie",
        "mood": "Mind-bending and Visually Stunning",
    }

    queries = main_module.build_candidate_queries(criteria)

    assert len(queries) >= 3
    assert any("Mind-bending and Visually Stunning" in query for query in queries)
    assert all("2023-2024" in query for query in queries)
