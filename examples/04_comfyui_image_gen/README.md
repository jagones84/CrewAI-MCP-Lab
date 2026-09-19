# Example 04 — ComfyUI Image Generation (MCP, full pipeline)

Minimal, complete CrewAI example that uses a **ComfyUI MCP server** for the four
canonical image operations: text-to-image generation, img2img modification,
upscaling, and background removal. Mirrors the same pattern used in
[Example 05](../05_illustrated_book_writer) and is built on top of the
[`comfyui-image-gen`](_skill_reference/openclaw_comfyui_image_gen/) skill
that lives on the DGX-SPARK-ETH machine under `~/.openclaw/`.

Out of the box it targets the **DGX Spark ComfyUI tunnel** (`comfyui-dgspark`
from the repo `crewai_mcp.json`), and gracefully falls back to a bundled
**mock ComfyUI server** so the example is runnable on any machine, including
CI.

## What it does

1. Loads the configuration from `config/preferences.yaml`.
2. Loads the `.env` from the repository root.
3. Picks the right ComfyUI MCP server (`comfyui-dgspark`, `comfyui`, or the
   bundled `comfyui-mock`).
4. Builds a single `Visual Designer` agent that gets the full ComfyUI MCP tool
   surface.
5. Runs the configured pipeline:
   * **`simple`** (default) — one `generate_image` call → one PNG.
   * **`full`** — `generate_image` → `modify_image` (img2img) → `upscale_image`,
     with an optional `remove_background` branch on the original.
6. Validates every output file exists and is non-empty on disk.

## ComfyUI tool surface

The example uses a single ComfyUI MCP server but exposes four tools,
mirroring the openclaw `comfyui-image-gen` skill:

| Tool                | Purpose                                      | Workflow JSON                                       |
|---------------------|----------------------------------------------|-----------------------------------------------------|
| `generate_image`    | text-to-image                                | `image_perfectDeliberate_text_to_image_API.json`    |
| `modify_image`      | img2img / image modification                 | `img2img_workflow.json`                             |
| `upscale_image`     | upscale an existing image                    | `upscale_workflow.json`                             |
| `remove_background` | strip the background of an existing image    | `remove_background_workflow.json`                   |
| `list_workflows`    | enumerate available workflow files           | —                                                   |

The exact same tools are exposed by the production `comfyui-dgspark` server
(reachable via the DGX tunnel) and by the bundled mock used during development
and CI.

## Pipeline modes

### `simple` (default)
Single text-to-image generation. One agent, one task, one output.

```bash
python src/main.py                  # pipeline: simple (from preferences.yaml)
python src/main.py --pipeline=simple
```

Output: `outputs/generated_image.png`.

### `full`
A real production chain that uses the same visual designer agent for all
operations:

1. `generate_image` → `outputs/generated.png` (text-to-image).
2. `modify_image`   → `outputs/modified.png`  (img2img refinement of step 1).
3. `upscale_image`  → `outputs/upscaled.png`  (quality-first 4x upscale of step 2).
4. `remove_background` → `outputs/no_bg.png`  (optional, runs on the original).

```bash
python src/main.py --pipeline=full
```

Per-step parameters (denoise, upscale model, edit prompt, optional bg-removal
model) are configured in `config/preferences.yaml` under the `run` section.

## Folder layout

```
examples/04_comfyui_image_gen/
├── _skill_reference/
│   ├── README.md
│   └── openclaw_comfyui_image_gen/    # Verbatim snapshot of the openclaw skill
├── config/
│   └── preferences.yaml                # LLM + ComfyUI + run + pipeline settings
├── log/
│   └── log.txt                          # Application log
├── outputs/
│   ├── generated_image.png              # Final image (simple pipeline)
│   ├── generated.png / modified.png /
│   │   upscaled.png / no_bg.png         # Full-pipeline artefacts
│   └── task_output.txt                  # Raw agent text output (proof of run)
├── scripts/
│   ├── start_tunnels.bat                # SSH tunnels for DGX Spark (ComfyUI :11002)
│   └── start_tunnels.sh
├── src/
│   ├── agents.py                        # Visual Designer agent
│   ├── tasks.py                         # generate / modify / upscale / remove_bg tasks
│   ├── main.py                          # Entry point (pipeline-aware)
│   ├── __init__.py
│   ├── config/
│   │   └── config.py                    # YAML loader
│   └── utils/
│       ├── comfy_check.py               # TCP pre-flight check
│       ├── llm_factory.py               # OpenRouter / OpenAI / Ollama / LlamaCpp wiring
│       └── logger.py                    # File + stdout logger
├── TEST/
│   └── mock_comfy_server.py             # Bundled mock MCP server (no GPU needed)
├── tests/
│   └── test_main.py                     # Regression suite (pytest)
├── .env.example                         # Template for repo root .env
├── .gitignore
├── README.md
├── requirements.txt
├── run.bat
└── run.sh
```

## Prerequisites

- **Python 3.10+**
- A ComfyUI instance reachable from your machine:
  - The **DGX Spark tunnel** at `127.0.0.1:11002` (recommended), or
  - A **local ComfyUI** at `127.0.0.1:8188`, or
  - Just rely on the bundled mock for development.

The production ComfyUI MCP server (`comfyui-dgspark`) automatically opens
its own SSH tunnel to DGX on first connection, so you do **not** need to
manually run the tunnel script if the MCP server is configured correctly
in `crewai_mcp.json`. The `scripts/start_tunnels.bat` file is kept as a
fallback for power users who want to manage the tunnel themselves.

## Installation

From the repository root:

```bash
pip install -r examples/04_comfyui_image_gen/requirements.txt
cp examples/04_comfyui_image_gen/.env.example .env
# fill in OPENAI_API_KEY or OPENROUTER_API_KEY
```

> The example loads the `.env` from the **repository root**, not from the
> example folder, so you can share credentials across all examples.

## Configure

Edit `config/preferences.yaml`:

```yaml
llm:
  provider: "openrouter"
  model: "google/gemini-2.5-flash-lite"

comfyui:
  mcp_server: "comfyui-dgspark"      # DGX Spark ComfyUI tunnel
  allow_mock_fallback: false         # set to true to silently fall back to the mock
  output_path: "outputs/generated_image.png"
  workflow: "image_perfectDeliberate_text_to_image_API.json"
  host: "127.0.0.1"
  port: 11002

run:
  pipeline: "full"                   # "simple" or "full"
  prompt: "A neon-lit cyberpunk dragon over Tokyo at night"
  negative_prompt: "blurry, low resolution, watermark"
  seed: 42
  denoise: 0.55                      # 0.25 light edit, 0.5-0.7 normal, 0.75+ strong
  upscale_model: "4x-UltraSharp.pth"
  also_remove_background: false
```

To target a local ComfyUI instead, just change `mcp_server: "comfyui"`. To
force the bundled mock (no GPU, no network), set `mcp_server: "comfyui-mock"`.

## Usage

```bash
python src/main.py                              # honours run.pipeline
python src/main.py --pipeline=simple            # one-shot image generation
python src/main.py --pipeline=full              # generate + modify + upscale
```

or use the convenience launchers:

```bash
run.bat          # Windows
./run.sh         # Linux / macOS
```

If the tool returns a path but the file is missing, a clear error is logged
along with the path the example expected.

## Run the tests

```bash
# From the repository root (or use the example's tests directly):
f:\REPOSITORIES\Crewai-mcp-lab\venv\Scripts\python.exe -m pytest \
    examples/04_comfyui_image_gen/tests
```

The suite covers (23 tests):

- repo-level `.env` path resolution
- config loader error paths
- mock ComfyUI server presence + tool surface parity
- OpenRouter normalization (stale model swap, prefix, API key wiring)
- `select_comfy_server_name` policy (live vs mock fallback)
- pipeline selection (`simple` vs `full`, with/without `also_remove_background`)
- `build_full_pipeline` task count and validation
- the bundled mock server writes a real PNG for every supported tool

## Reference: openclaw `comfyui-image-gen` skill

The skill in `_skill_reference/openclaw_comfyui_image_gen/` is a verbatim
snapshot of `Z:\.openclaw\workspace\skills\comfyui-image-gen` (DGX Spark
home directory). It contains the original Python scripts and shell wrappers
that we adapted into the CrewAI MCP tools:

- `scripts/generate_and_send.py` → `generate_image`
- `scripts/modify_and_send.py`   → `modify_image`
- `scripts/upscale_and_send.py`  → `upscale_image`
- `scripts/remove_bg_and_send.py`→ `remove_background`

See `_skill_reference/README.md` for the exact mapping and the differences
between the openclaw CLI skill and the CrewAI version.

## Troubleshooting

- **`Image generation finished but no file was produced`** — ComfyUI on the
  DGX requires a *file* path (not a directory) in the `output_path` argument.
  The example always passes a full file path from `preferences.yaml`;
  double-check the values for `output_path`, `modified_path`, etc.
- **`comfyui-dgspark` not in `crewai_mcp.json`** — make sure you pulled the
  latest `crewai_mcp.json` from the repository root. The mock fallback will
  still let you iterate locally.
- **Live ComfyUI is not reachable and the example keeps using the mock** —
  set `comfyui.allow_mock_fallback: false` to make the failure visible,
  then fix the tunnel.
- **`modify_image` produced something too close to the original** — bump
  `run.denoise` (0.5–0.7 is the sweet spot for normal edits).
- **`upscale_image` complains the model is not installed** — the DGX
  ComfyUI must have `4x-UltraSharp.pth` (or whatever model you named in
  `run.upscale_model`) in its `models/upscale_models/` directory.
- **OpenRouter auth errors** — the example looks for `OPENROUTER_API_KEY`
  first, then falls back to `OPENAI_API_KEY`. The repo root `.env` is the
  source of truth.
