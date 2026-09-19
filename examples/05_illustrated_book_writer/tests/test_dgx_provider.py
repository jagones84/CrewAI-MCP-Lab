import os

from src import main as main_module
from src.agents import agents as agents_module


def test_tunneled_dgx_profile_is_treated_as_openai_compatible():
    effective_model = agents_module.resolve_llm_model_name(
        "qwen-3.6-35b-a3b-claude47-opus-abliterated",
        "http://localhost:11003/v1",
    )

    assert effective_model == "openai/qwen-3.6-35b-a3b-claude47-opus-abliterated"


def test_dgx_llm_omits_empty_tools_and_forces_stop_sentinel():
    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    params = llm._prepare_completion_params("hello", tools=[])

    assert "tools" not in params
    assert params["stop"] == [agents_module.DGXCompatibleLLM.SAFE_STOP_SENTINEL]


def test_dgx_llm_replaces_react_observation_stop_with_sentinel():
    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
        stop=[agents_module.DGXCompatibleLLM.REACT_OBSERVATION_STOP],
    )

    params = llm._prepare_completion_params(
        [
            {"role": "system", "content": "system"},
            {"role": "user", "content": "user"},
        ],
        tools=None,
    )

    assert params["stop"] == [agents_module.DGXCompatibleLLM.SAFE_STOP_SENTINEL]


def test_book_agents_uses_dgx_compatible_llm_for_local_openai_endpoint():
    agents = agents_module.BookAgents(
        config={
            "agents": {
                "llm": {
                    "model": "qwen-3.6-35b-a3b-claude47-opus-abliterated",
                    "base_url": "http://localhost:11003/v1",
                    "temperature": 0.7,
                }
            }
        }
    )

    assert isinstance(agents._llm, agents_module.DGXCompatibleLLM)


def test_dgx_llm_logs_request_shape_summary():
    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    summary = llm._build_request_shape_summary(
        {
            "model": "openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
            "messages": [{"role": "user", "content": "hello world"}],
            "stop": [agents_module.DGXCompatibleLLM.SAFE_STOP_SENTINEL],
        }
    )

    assert summary["model"] == "openai/qwen-3.6-35b-a3b-claude47-opus-abliterated"
    assert summary["message_count"] == 1
    assert summary["content_chars"] == len("hello world")
    assert summary["has_tools"] is False
    assert summary["stop"] == [agents_module.DGXCompatibleLLM.SAFE_STOP_SENTINEL]


def test_dgx_llm_applies_default_max_tokens_when_missing():
    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    params = llm._prepare_completion_params("hello", tools=None)

    assert params["max_tokens"] == 4096


def test_dgx_llm_preserves_explicit_max_tokens():
    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
        max_tokens=1024,
    )

    params = llm._prepare_completion_params("hello", tools=None)

    assert params["max_tokens"] == 1024


def test_dgx_llm_retries_retryable_bad_request_once(monkeypatch):
    calls = {"count": 0}

    class DummyResponse:
        status_code = 400

    class DummyBadRequestError(Exception):
        def __init__(self):
            super().__init__("OpenAIException - Error code: 400")
            self.response = DummyResponse()

    def fake_call(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise DummyBadRequestError()
        return "ok"

    monkeypatch.setattr(agents_module.LLM, "call", fake_call)

    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    result = llm.call("hello")

    assert result == "ok"
    assert calls["count"] == 2


def test_dgx_llm_retries_stringified_bad_request_without_response(monkeypatch):
    calls = {"count": 0}

    class DummyBadRequestError(Exception):
        pass

    def fake_call(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise DummyBadRequestError("litellm.BadRequestError: OpenAIException - Error code: 400")
        return "ok"

    monkeypatch.setattr(agents_module.LLM, "call", fake_call)

    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    result = llm.call("hello")

    assert result == "ok"
    assert calls["count"] == 2


def test_dgx_llm_retries_up_to_three_attempts(monkeypatch):
    calls = {"count": 0}

    class DummyBadRequestError(Exception):
        pass

    def fake_call(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] < 3:
            raise DummyBadRequestError("litellm.BadRequestError: OpenAIException - Error code: 400")
        return "ok"

    monkeypatch.setattr(agents_module.LLM, "call", fake_call)

    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    result = llm.call("hello")

    assert result == "ok"
    assert calls["count"] == 3


def test_dgx_llm_retries_timeout_errors(monkeypatch):
    calls = {"count": 0}

    def fake_call(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise TimeoutError("timed out waiting for response")
        return "ok"

    monkeypatch.setattr(agents_module.LLM, "call", fake_call)

    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    result = llm.call("hello")

    assert result == "ok"
    assert calls["count"] == 2


def test_dgx_llm_retries_connection_errors(monkeypatch):
    calls = {"count": 0}

    class DummyConnectionError(Exception):
        pass

    def fake_call(self, *args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            raise DummyConnectionError(
                "litellm.InternalServerError: InternalServerError: OpenAIException - Connection error."
            )
        return "ok"

    monkeypatch.setattr(agents_module.LLM, "call", fake_call)

    llm = agents_module.DGXCompatibleLLM(
        model="openai/qwen-3.6-35b-a3b-claude47-opus-abliterated",
        api_key="EMPTY",
        base_url="http://localhost:11003/v1",
        temperature=0.7,
    )

    result = llm.call("hello")

    assert result == "ok"
    assert calls["count"] == 2


def test_remote_llama_cpp_profile_does_not_start_local_server(monkeypatch):
    config = {"agents": {"llm": {}}}
    infra = {
        "llm_selected": "qwen_abliterated_dgx",
        "llm_profiles": {
            "qwen_abliterated_dgx": {
                "model": "qwen-3.6-35b-a3b-claude47-opus-abliterated",
                "base_url": "http://localhost:11003/v1",
                "temperature": 0.7,
                "api_key": "EMPTY",
                "provider_kind": "llama_cpp_remote",
            }
        },
    }
    llama_calls = []
    ollama_calls = []

    class DummyLlamaController:
        def __init__(self, profile):
            llama_calls.append(("init", profile["provider_kind"]))

        def ensure_server_running(self):
            llama_calls.append(("ensure_server_running", None))

    class DummyOllamaController:
        def __init__(self, profile):
            ollama_calls.append(("init", profile["provider_kind"]))

        def start_server(self):
            ollama_calls.append(("start_server", None))

        def load_model(self):
            ollama_calls.append(("load_model", None))

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    selected = main_module.apply_selected_llm_profile(
        config,
        infra,
        llama_controller_cls=DummyLlamaController,
        ollama_controller_cls=DummyOllamaController,
    )

    assert selected["provider_kind"] == "llama_cpp_remote"
    assert config["agents"]["llm"]["model"] == "qwen-3.6-35b-a3b-claude47-opus-abliterated"
    assert config["agents"]["llm"]["base_url"] == "http://localhost:11003/v1"
    assert os.environ["OPENAI_API_KEY"] == "EMPTY"
    assert llama_calls == []
    assert ollama_calls == []


def test_local_llama_cpp_profile_starts_managed_server(monkeypatch):
    config = {"agents": {"llm": {}}}
    infra = {
        "llm_selected": "llama_cp_local",
        "llm_profiles": {
            "llama_cp_local": {
                "model": "Cydonia-24B-v4j-Q4_K_M.gguf",
                "base_url": "http://localhost:8080/v1",
                "temperature": 0.4,
                "api_key": "EMPTY",
                "provider_kind": "llama_cpp_local",
            }
        },
    }
    llama_calls = []

    class DummyLlamaController:
        def __init__(self, profile):
            llama_calls.append(("init", profile["provider_kind"]))

        def ensure_server_running(self):
            llama_calls.append(("ensure_server_running", None))

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    selected = main_module.apply_selected_llm_profile(
        config,
        infra,
        llama_controller_cls=DummyLlamaController,
        ollama_controller_cls=None,
    )

    assert selected["provider_kind"] == "llama_cpp_local"
    assert config["agents"]["llm"]["model"] == "Cydonia-24B-v4j-Q4_K_M.gguf"
    assert llama_calls == [
        ("init", "llama_cpp_local"),
        ("ensure_server_running", None),
    ]


def test_extract_writing_style_reads_story_content_settings():
    writing_style = main_module.extract_writing_style(
        {
            "story": {
                "content": {
                    "word_count": 800,
                    "language": "Italian",
                    "tone": "Gothic",
                }
            }
        }
    )

    assert writing_style["word_count"] == 800
    assert writing_style["language"] == "Italian"
    assert writing_style["tone"] == "Gothic"
