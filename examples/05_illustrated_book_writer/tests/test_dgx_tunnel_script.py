from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


EXAMPLE_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = EXAMPLE_ROOT / "scripts" / "test_dgx_llm_tunnel.py"
TUNNEL_BATCH_PATH = EXAMPLE_ROOT / "scripts" / "start_tunnels.bat"
README_PATH = EXAMPLE_ROOT / "README.md"


def load_script_module():
    """Load the DGX preflight script as a Python module."""
    spec = spec_from_file_location("dgx_tunnel_script", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_preflight_script_exists_and_targets_dgx_tunnel():
    assert SCRIPT_PATH.exists(), f"Missing expected script: {SCRIPT_PATH}"

    script = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "/v1/models" in script
    assert "/v1/chat/completions" in script
    assert "localhost:11003" in script
    assert "qwen-3.6-35b-a3b-claude47-opus-abliterated" in script


def test_preflight_script_calls_models_and_chat_completion(monkeypatch):
    module = load_script_module()
    requests = []

    class DummyResponse:
        def __init__(self, payload: str):
            self.payload = payload

        def read(self) -> bytes:
            return self.payload.encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    def fake_urlopen(request_obj, timeout):
        requests.append((request_obj, timeout))
        url = getattr(request_obj, "full_url", request_obj)

        if url.endswith("/models"):
            return DummyResponse('{"data": [{"id": "qwen-3.6-35b-a3b-claude47-opus-abliterated"}]}')

        return DummyResponse(
            '{"choices": [{"message": {"content": "OK"}}]}'
        )

    monkeypatch.setattr(module.request, "urlopen", fake_urlopen)

    models_payload = module.fetch_models()
    chat_payload = module.tiny_chat()

    assert models_payload["data"][0]["id"] == "qwen-3.6-35b-a3b-claude47-opus-abliterated"
    assert chat_payload["choices"][0]["message"]["content"] == "OK"
    assert str(requests[0][0]).endswith("/v1/models")
    assert requests[1][0].full_url.endswith("/v1/chat/completions")
    assert requests[1][0].headers["Content-type"] == "application/json"


def test_start_tunnels_script_mentions_dgx_llama_default():
    script = TUNNEL_BATCH_PATH.read_text(encoding="utf-8")

    assert "11003:localhost:8092" in script
    assert "default" in script.lower()
    assert "qwen" in script.lower() or "llama" in script.lower()
    assert "optional fallback" in script.lower()


def test_readme_documents_dgx_first_but_keeps_other_llm_options():
    readme = README_PATH.read_text(encoding="utf-8")

    assert "DGX Spark Default Setup" in readme
    assert "qwen_abliterated_dgx" in readme
    assert "scripts\\start_tunnels.bat" in readme
    assert "python scripts\\test_dgx_llm_tunnel.py" in readme
    assert "llama_cp_local" in readme
    assert "ollama" in readme
    assert "openrouter" in readme
    assert "llama_cp" in readme
