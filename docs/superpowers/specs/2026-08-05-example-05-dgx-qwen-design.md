# Example 05 DGX Qwen Design

## Goal

Make `examples/05_illustrated_book_writer` use a DGX Spark-hosted `llama.cpp` server over SSH tunnel as the default LLM path, with Qwen Abliterated as the default model/profile, while keeping the existing local providers as fallback options.

The DGX server is assumed to already be running with the correct model loaded. Example 05 must not start or manage the remote server. It must only:

- use the existing SSH-tunnel workflow,
- validate the tunnel and OpenAI-compatible endpoint,
- select the DGX profile by default in config,
- document the workflow clearly in the example README.

## Constraints

- SSH only. No remote startup orchestration.
- DGX Spark is the new default path for example 05.
- Existing local profiles such as `llama_cp_local`, `ollama`, `openrouter`, and generic external profiles must remain available.
- The example must keep the current config-driven profile selection pattern rather than introducing hardcoded provider logic.
- Preflight checks must be lightweight and safe to run before a full book generation.

## Current State

Example 05 already has most of the required plumbing:

- `config/config.yaml` contains `infrastructure.llm_selected` and `llm_profiles`.
- `src/main.py` loads the selected LLM profile and injects it into the CrewAI agent config.
- `scripts/start_tunnels.bat` already opens:
  - `11002 -> 8188` for ComfyUI,
  - `11435 -> 11434` for Ollama,
  - `11003 -> 11005` for `llama.cpp`.

The missing pieces are:

- a DGX-first default profile and naming,
- a clear distinction between local auto-managed `llama_cp_local` and remote external `llama_cp_dgx`,
- explicit preflight validation scripts and documented usage,
- README and config updates that make DGX the primary supported workflow.

## Desired User Flow

1. The user ensures the DGX `llama.cpp` server is already running with the intended Qwen Abliterated model.
2. The user runs `scripts/start_tunnels.bat` locally.
3. The user runs a small preflight test script to confirm:
   - local tunnel port is reachable,
   - `/v1/models` responds,
   - a tiny chat completion succeeds.
4. The user runs `python src/main.py`.
5. Example 05 uses the DGX tunneled profile by default.

## Design

### 1. Config Changes

`examples/05_illustrated_book_writer/config/config.yaml` will be updated so that:

- `infrastructure.llm_selected` defaults to a DGX profile, recommended name: `qwen_abliterated_dgx`.
- A dedicated DGX external profile is added under `llm_profiles`.
- Existing local and fallback profiles remain in the file.

Recommended profile shape:

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
      expected_remote_service: "DGX Spark llama.cpp"
```

The profile remains OpenAI-compatible and intentionally mirrors the way external/local `llama.cpp` profiles are already consumed by `main.py`.

### 2. Runtime Behavior

`src/main.py` will continue to use the selected profile and inject:

- `model`
- `base_url`
- `temperature`
- `api_key`

No local `llama.cpp` process should be started for the DGX profile.

Behavior split:

- `llama_cp_local`: auto-managed local process via `LlamaController`
- `ollama`: local process management via `OllamaController`
- `qwen_abliterated_dgx` and similar remote tunneled profiles: external endpoint only, no auto-start

If needed, the profile-selection logic will be refined so remote tunneled `llama.cpp` profiles do not accidentally fall into local auto-management logic simply because their name contains `llama_cp`.

### 3. Tunnel Script

`scripts/start_tunnels.bat` will be updated to present DGX as the primary/default workflow.

The script should:

- clearly label the `11003 -> 11005` mapping as the default example 05 LLM path,
- keep the ComfyUI tunnel,
- keep the Ollama tunnel only if it still provides value as a fallback.

The script does not need to become interactive. It only needs clearer defaults and comments.

### 4. Preflight Test Script

A small script will be added under `examples/05_illustrated_book_writer/scripts/`, for example:

- `test_dgx_llm_tunnel.py`

The script should:

- call `GET /v1/models`,
- print the returned model list,
- issue one minimal chat completion against the tunneled endpoint,
- fail with clear, actionable errors if the tunnel or server is unavailable.

This script is intentionally separate from the main flow so the user can validate infrastructure before a full run.

### 5. README Changes

`examples/05_illustrated_book_writer/README.md` will be updated so DGX is the primary path, not an optional aside.

The README should:

- present DGX Spark + SSH tunnel as the default setup,
- state that the remote `llama.cpp` server must already be running,
- document the local tunnel script,
- document the preflight test script,
- show `qwen_abliterated_dgx` as the default config selection,
- keep local `llama_cp_local` and `ollama` sections as fallback alternatives.

### 6. Testing

Implementation validation should include:

- config load verification with DGX profile selected,
- local preflight script success against the tunnel,
- confirmation that `src/main.py` announces the DGX profile correctly,
- confirmation that no local `llama-server.exe` auto-start is attempted when the DGX profile is selected.

Full book generation is out of scope for this feature spec, except for confirming that startup uses the DGX profile correctly.

## Files Expected To Change

- `examples/05_illustrated_book_writer/config/config.yaml`
- `examples/05_illustrated_book_writer/scripts/start_tunnels.bat`
- `examples/05_illustrated_book_writer/scripts/test_dgx_llm_tunnel.py`
- `examples/05_illustrated_book_writer/src/main.py`
- `examples/05_illustrated_book_writer/README.md`

Conditional change if endpoint-format tests require it:

- `examples/05_illustrated_book_writer/src/agents/agents.py`

This file will only be changed if the DGX tunneled endpoint fails model-prefix handling or local OpenAI-compatible endpoint detection during implementation tests.

## Risks

- The DGX server may be running on a different port than the current tunnel expects.
- The reported Qwen long context may not be available in practice unless the remote server was started with an appropriate `--ctx-size`.
- Example 05 may still require prompt-budget fixes independent of the DGX model switch.
- If the remote endpoint returns a model alias different from the configured profile name, the OpenAI-compatible wrapper may require minor adjustment.

## Non-Goals

- Starting or stopping the DGX remote server from the example.
- Automatically selecting models on the remote machine.
- Reworking the narrative prompt-budget system beyond what is already required for existing full-run stability.
- Replacing ComfyUI or changing the image-generation architecture.

## Acceptance Criteria

- `config.yaml` defaults to the DGX Qwen Abliterated profile.
- `start_tunnels.bat` clearly supports the DGX default workflow.
- A local preflight script can verify `/v1/models` and a tiny completion via the tunnel.
- `src/main.py` uses the DGX profile without attempting local `llama.cpp` startup.
- `README.md` documents DGX Spark as the main recommended path for example 05.
