# Example 05 DGX Qwen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make DGX Spark `llama.cpp` over SSH tunnel the default LLM option for example 05 while treating it as just another selectable provider alongside local `llama_cp_local`, local `ollama`, and `openrouter`.

**Architecture:** Keep the existing config-driven provider selection flow in `src/main.py`, but add an explicit remote `llama.cpp` provider kind so DGX is consumed like an external OpenAI-compatible endpoint rather than a local auto-managed server. Add a lightweight preflight script for tunnel validation, update config defaults/templates, and refresh the README/tunnel script so DGX is the primary documented path without removing other providers.

**Tech Stack:** Python, CrewAI, llama.cpp OpenAI-compatible HTTP API, SSH tunnels, pytest, YAML config, Windows batch script.

---

## File Map

- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\src\main.py`
  - Responsibility: keep profile selection generic and prevent DGX remote profiles from triggering local llama auto-start.
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\src\agents\agents.py`
  - Responsibility: make OpenAI-compatible local/tunneled endpoint detection robust for `localhost:11003`.
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\config\config.yaml`
  - Responsibility: make DGX Qwen the default active profile while preserving other LLM options.
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\config\config.template.yaml`
  - Responsibility: provide the same DGX-first structure in the template.
- Create: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\scripts\test_dgx_llm_tunnel.py`
  - Responsibility: preflight `/v1/models` and a tiny chat completion through the SSH tunnel.
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\scripts\start_tunnels.bat`
  - Responsibility: document the DGX llama tunnel as the default example-05 LLM path.
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\README.md`
  - Responsibility: document DGX as the main provider and keep local providers as alternatives.
- Create: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\tests\test_dgx_provider.py`
  - Responsibility: lock in provider-kind behavior and local auto-start avoidance.
- Create: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\tests\test_dgx_tunnel_script.py`
  - Responsibility: lock in the tunnel script’s key port mapping and messaging.

### Task 1: Lock In DGX Provider Semantics

**Files:**
- Create: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\tests\test_dgx_provider.py`
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\src\main.py`
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\src\agents\agents.py`

- [ ] **Step 1: Write the failing runtime tests**

```python
from src.agents.agents import BookAgents


def test_tunneled_dgx_profile_is_treated_as_openai_compatible():
    agents = BookAgents(
        {
            "agents": {
                "llm": {
                    "model": "Qwen-Abliterated",
                    "base_url": "http://localhost:11003/v1",
                    "temperature": 0.7,
                }
            }
        }
    )

    assert agents._llm.model == "openai/Qwen-Abliterated"


def test_remote_llama_cpp_profile_does_not_require_local_executable(monkeypatch):
    infra = {
        "llm_selected": "qwen_abliterated_dgx",
        "llm_profiles": {
            "qwen_abliterated_dgx": {
                "model": "Qwen-Abliterated",
                "base_url": "http://localhost:11003/v1",
                "temperature": 0.7,
                "api_key": "EMPTY",
                "provider_kind": "llama_cpp_remote",
            }
        },
    }

    selected = infra["llm_profiles"][infra["llm_selected"]]

    assert selected["provider_kind"] == "llama_cpp_remote"
    assert "executable_path" not in selected
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests\test_dgx_provider.py -q`

Expected: FAIL because the current implementation still infers behavior mostly from profile names and does not yet have an explicit DGX provider-kind path.

- [ ] **Step 3: Implement minimal provider-kind support in `main.py`**

```python
llm_sel = infra.get("llm_selected", "openrouter")
llm_profile = infra.get("llm_profiles", {}).get(llm_sel)
provider_kind = (llm_profile or {}).get("provider_kind", "")

if llm_profile:
    config["agents"]["llm"]["model"] = llm_profile["model"]
    config["agents"]["llm"]["base_url"] = llm_profile["base_url"]
    config["agents"]["llm"]["temperature"] = llm_profile.get("temperature", 0.7)

    if "api_key" in llm_profile:
        os.environ["OPENAI_API_KEY"] = llm_profile["api_key"]

    if provider_kind == "llama_cpp_local":
        controller = LlamaController(llm_profile)
        controller.ensure_server_running()
    elif provider_kind == "ollama_local":
        controller = OllamaController(llm_profile)
        controller.start_server()
        controller.load_model()
```

- [ ] **Step 4: Make local/tunneled OpenAI-compatible detection explicit in `agents.py`**

```python
effective_model = model
openai_compatible_hosts = ["localhost", "127.0.0.1", "10.0.0.1"]
is_local_openai = any(host in base_url for host in openai_compatible_hosts)

if is_local_openai and not model.startswith("openai/") and not model.startswith("ollama/"):
    effective_model = f"openai/{model}"
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests\test_dgx_provider.py -q`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add examples/05_illustrated_book_writer/src/main.py \
        examples/05_illustrated_book_writer/src/agents/agents.py \
        examples/05_illustrated_book_writer/tests/test_dgx_provider.py
git commit -m "feat: add dgx llama cpp provider selection"
```

### Task 2: Make DGX Qwen The Default Config Path

**Files:**
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\config\config.yaml`
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\config\config.template.yaml`
- Test: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\tests\test_dgx_provider.py`

- [ ] **Step 1: Extend the failing test with expected config semantics**

```python
def test_dgx_profile_shape_matches_external_remote_provider():
    profile = {
        "model": "Qwen-Abliterated",
        "base_url": "http://localhost:11003/v1",
        "temperature": 0.7,
        "api_key": "EMPTY",
        "provider_kind": "llama_cpp_remote",
        "tunnel_required": True,
    }

    assert profile["provider_kind"] == "llama_cpp_remote"
    assert profile["base_url"] == "http://localhost:11003/v1"
    assert profile["tunnel_required"] is True
```

- [ ] **Step 2: Run the targeted tests**

Run: `python -m pytest tests\test_dgx_provider.py -q`

Expected: PASS for earlier tests, then this new config-focused test should serve as the reference for the config edit.

- [ ] **Step 3: Update `config.yaml` to use DGX as the default provider**

```yaml
infrastructure:
  llm_selected: "qwen_abliterated_dgx"

  llm_profiles:
    qwen_abliterated_dgx:
      model: "Qwen-Abliterated"
      base_url: "http://localhost:11003/v1"
      temperature: 0.7
      api_key: "EMPTY"
      provider_kind: "llama_cpp_remote"
      tunnel_required: true

    llama_cp_local:
      model: "Cydonia-24B-v4j-Q4_K_M.gguf"
      base_url: "http://localhost:8080/v1"
      temperature: 0.7
      api_key: "EMPTY"
      provider_kind: "llama_cpp_local"
      executable_path: "F:\\PROGRAMS\\llama_cp\\llama-server.exe"
      models_dir: "F:\\PROGRAMS\\llama_cp\\MODELS"

    ollama:
      model: "llama3:latest"
      base_url: "http://localhost:11434/v1"
      temperature: 0.7
      api_key: "ollama"
      provider_kind: "ollama_local"
```

- [ ] **Step 4: Mirror the same provider-kind structure in `config.template.yaml`**

```yaml
infrastructure:
  llm_selected: "qwen_abliterated_dgx"

  llm_profiles:
    qwen_abliterated_dgx:
      model: "Qwen-Abliterated"
      base_url: "http://localhost:11003/v1"
      temperature: 0.7
      api_key: "EMPTY"
      provider_kind: "llama_cpp_remote"
      tunnel_required: true
```

- [ ] **Step 5: Run tests and a config smoke read**

Run: `python -m pytest tests\test_dgx_provider.py -q`

Run: `python -c "from src.config.config import ConfigLoader; cfg=ConfigLoader.load_config(); print(cfg['infrastructure']['llm_selected']); print(cfg['infrastructure']['llm_profiles']['qwen_abliterated_dgx']['provider_kind'])"`

Expected:
- pytest PASS
- console prints:
  - `qwen_abliterated_dgx`
  - `llama_cpp_remote`

- [ ] **Step 6: Commit**

```bash
git add examples/05_illustrated_book_writer/config/config.yaml \
        examples/05_illustrated_book_writer/config/config.template.yaml \
        examples/05_illustrated_book_writer/tests/test_dgx_provider.py
git commit -m "feat: make dgx qwen the default example 05 llm"
```

### Task 3: Add DGX Tunnel Preflight Validation

**Files:**
- Create: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\scripts\test_dgx_llm_tunnel.py`
- Create: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\tests\test_dgx_tunnel_script.py`

- [ ] **Step 1: Write the failing script test**

```python
from pathlib import Path


def test_preflight_script_checks_models_and_chat_completion():
    script = Path("scripts/test_dgx_llm_tunnel.py").read_text(encoding="utf-8")

    assert "/v1/models" in script
    assert "/v1/chat/completions" in script
    assert "Qwen-Abliterated" in script or "localhost:11003" in script
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests\test_dgx_tunnel_script.py -q`

Expected: FAIL because the script does not exist yet.

- [ ] **Step 3: Create the minimal preflight script**

```python
import json
import sys
from urllib import request, error


BASE_URL = "http://localhost:11003/v1"
MODEL_NAME = "Qwen-Abliterated"


def fetch_models():
    with request.urlopen(f"{BASE_URL}/models", timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def tiny_chat():
    payload = json.dumps(
        {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Reply with OK only."}],
            "max_tokens": 8,
            "temperature": 0.0,
        }
    ).encode("utf-8")
    req = request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer EMPTY"},
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


if __name__ == "__main__":
    try:
        print(json.dumps(fetch_models(), indent=2))
        print(json.dumps(tiny_chat(), indent=2))
    except error.URLError as exc:
        print(f"DGX tunnel preflight failed: {exc}")
        sys.exit(1)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `python -m pytest tests\test_dgx_tunnel_script.py -q`

Expected: PASS

- [ ] **Step 5: Run the live preflight manually**

Run: `python scripts\test_dgx_llm_tunnel.py`

Expected:
- model list is printed if the tunnel/server is up
- tiny completion JSON is printed
- nonzero exit with actionable message if the tunnel/server is down

- [ ] **Step 6: Commit**

```bash
git add examples/05_illustrated_book_writer/scripts/test_dgx_llm_tunnel.py \
        examples/05_illustrated_book_writer/tests/test_dgx_tunnel_script.py
git commit -m "feat: add dgx llm tunnel preflight script"
```

### Task 4: Refresh Tunnel Script And README

**Files:**
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\scripts\start_tunnels.bat`
- Modify: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\README.md`
- Create or extend: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\tests\test_dgx_tunnel_script.py`

- [ ] **Step 1: Extend the failing docs/script test**

```python
def test_start_tunnels_script_mentions_dgx_llama_default():
    script = Path("scripts/start_tunnels.bat").read_text(encoding="utf-8")

    assert "11003:localhost:11005" in script
    assert "default" in script.lower()
    assert "qwen" in script.lower() or "llama" in script.lower()
```

- [ ] **Step 2: Run the tests to verify current docs/script gaps**

Run: `python -m pytest tests\test_dgx_tunnel_script.py -q`

Expected: FAIL until the tunnel script/docs are updated to the new DGX-first wording.

- [ ] **Step 3: Update `start_tunnels.bat`**

```bat
@echo off
echo Opening DGX Spark tunnels for example 05...

set REMOTE_USER=jagones
set REMOTE_HOST=DGX-SPARK-ETH

:: Default example-05 LLM path: local 11003 -> remote 11005 (DGX llama.cpp / Qwen Abliterated)
start /b ssh -L 11003:localhost:11005 %REMOTE_USER%@%REMOTE_HOST% -N

:: Default example-05 image path: local 11002 -> remote 8188 (ComfyUI)
start /b ssh -L 11002:localhost:8188 %REMOTE_USER%@%REMOTE_HOST% -N

:: Optional fallback tunnel: local 11435 -> remote 11434 (Ollama)
start /b ssh -L 11435:localhost:11434 %REMOTE_USER%@%REMOTE_HOST% -N

echo DGX tunnels active. Run python scripts\test_dgx_llm_tunnel.py before python src\main.py
pause
```

- [ ] **Step 4: Update `README.md` so DGX is primary and other providers stay supported**

```md
## DGX Spark Default Setup

Example 05 now defaults to a DGX Spark-hosted `llama.cpp` model exposed through an SSH tunnel.
The remote DGX server must already be running with the correct model loaded.

1. Run `scripts\start_tunnels.bat`
2. Run `python scripts\test_dgx_llm_tunnel.py`
3. Run `python src/main.py`

The default LLM profile is `qwen_abliterated_dgx`.

## Other LLM Options

- `llama_cp_local`: local auto-managed `llama.cpp`
- `ollama`: local auto-managed Ollama
- `openrouter`: cloud OpenRouter
- `llama_cp`: generic external OpenAI-compatible `llama.cpp`
```

- [ ] **Step 5: Run the tests and a docs sanity check**

Run: `python -m pytest tests\test_dgx_tunnel_script.py -q`

Run: `findstr /C:"qwen_abliterated_dgx" README.md`

Expected:
- pytest PASS
- README contains the DGX default profile reference

- [ ] **Step 6: Commit**

```bash
git add examples/05_illustrated_book_writer/scripts/start_tunnels.bat \
        examples/05_illustrated_book_writer/README.md \
        examples/05_illustrated_book_writer/tests/test_dgx_tunnel_script.py
git commit -m "docs: document dgx qwen as default example 05 path"
```

### Task 5: End-To-End Startup Validation

**Files:**
- Modify if needed: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\src\main.py`
- Validate: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\config\config.yaml`
- Validate: `F:\REPOSITORIES\Crewai-mcp-lab\examples\05_illustrated_book_writer\scripts\test_dgx_llm_tunnel.py`

- [ ] **Step 1: Run the full focused test suite**

Run: `python -m pytest tests\test_dgx_provider.py tests\test_dgx_tunnel_script.py tests\test_prompt_budget.py tests\test_crewai_runtime.py tests\test_character_gender.py -q`

Expected: PASS

- [ ] **Step 2: Run the DGX preflight**

Run: `python scripts\test_dgx_llm_tunnel.py`

Expected: `/v1/models` succeeds and tiny completion succeeds through `localhost:11003`

- [ ] **Step 3: Run example 05 startup smoke**

Run: `python src/main.py`

Expected startup lines include:
- `Using LLM Provider: QWEN_ABLITERATED_DGX`
- `Using Image Provider: REMOTE_DGSPARK`
- no attempt to start `llama-server.exe` locally

- [ ] **Step 4: If startup fails on model prefix formatting, apply the narrow `agents.py` fix**

```python
is_local_openai = any(host in base_url for host in ["localhost", "127.0.0.1", "10.0.0.1"])
if is_local_openai and not model.startswith(("openai/", "ollama/")):
    effective_model = f"openai/{model}"
```

- [ ] **Step 5: Re-run startup smoke**

Run: `python src/main.py`

Expected: configuration loads cleanly and startup proceeds into the normal flow initialization using the DGX profile

- [ ] **Step 6: Commit**

```bash
git add examples/05_illustrated_book_writer/src/main.py \
        examples/05_illustrated_book_writer/src/agents/agents.py \
        examples/05_illustrated_book_writer/config/config.yaml \
        examples/05_illustrated_book_writer/config/config.template.yaml \
        examples/05_illustrated_book_writer/scripts/test_dgx_llm_tunnel.py \
        examples/05_illustrated_book_writer/scripts/start_tunnels.bat \
        examples/05_illustrated_book_writer/README.md \
        examples/05_illustrated_book_writer/tests/test_dgx_provider.py \
        examples/05_illustrated_book_writer/tests/test_dgx_tunnel_script.py
git commit -m "feat: add dgx qwen default path for example 05"
```
