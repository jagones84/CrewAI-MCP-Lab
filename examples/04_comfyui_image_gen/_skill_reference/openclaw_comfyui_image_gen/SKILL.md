---
name: comfyui-image-gen
description: Single uncensored image creation and processing skill for local ComfyUI. Use it for generation, upscaling, background removal, and image-to-image modification.
---

# ComfyUI Image Creation And Processing - Canonical Workflow

## Scope

This is the single image skill currently enabled for ComfyUI work.

Use it for:

- generating a new image from a prompt
- upscaling an existing image
- removing the background from an existing image
- modifying or restyling an existing image

Do not invent a separate ad-hoc image workflow outside this skill unless you are explicitly debugging ComfyUI itself.

## One Allowed Path Per Job Type

Do not manually reconstruct the workflow with separate `curl`, `ls`, `cp`, and `message` steps unless you are explicitly debugging the skill itself.

For generation, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/generate_and_send.py "<prompt>" <width> <height> generated.png
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-gen.sh "<prompt>" <width> <height> generated.png
```

The script already does all of this:

- submit to ComfyUI
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

## Upscaling Existing Images

For upscaling, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/upscale_and_send.py \
  /absolute/source/image.png upscaled.png 4x-UltraSharp.pth
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-upscale.sh \
  /absolute/source/image.png upscaled.png 4x-UltraSharp.pth
```

The script already does all of this:

- upload the source image to ComfyUI correctly
- submit a known-good upscale workflow
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

Required tool behavior:

1. Run the canonical upscale script once.
2. Read the final `READY_TO_SEND:` line.
3. Call the `message` tool once with that workspace path.
4. Only after a successful send, reply with the confirmation text.

Important:

- `4x-UltraSharp.pth` is the current quality-first default.
- `RealESRGAN_x4plus.pth` is acceptable later if installed and a more conservative photo-style result is wanted.
- Never use `resize_image`, `get_image`, `mcporter`, or handwritten `/prompt` JSON for normal upscale requests.
- Never pass a workspace absolute path directly into a raw `LoadImage` node.

## Removing Backgrounds

For background removal, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/remove_bg_and_send.py \
  /absolute/source/image.png removed_bg.png
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-remove-bg.sh \
  /absolute/source/image.png removed_bg.png
```

The script already does all of this:

- upload the source image to ComfyUI correctly
- submit a known-good background removal workflow
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

Important:

- This path uses the installed `LayerMask: RemBgUltra` node from `ComfyUI_LayerStyle`.
- The `RMBG-1.4` model may need to exist locally before the first run is fast.
- Never use the old `remove_background_workflow.json` path unless you are explicitly debugging the MCP repo itself.

## Modifying Existing Images

For image-to-image modification, normal use MUST go through exactly one command:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/modify_and_send.py \
  /absolute/source/image.png "your edit prompt" modified.png 0.55
```

Equivalent wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-modify.sh \
  /absolute/source/image.png "your edit prompt" modified.png 0.55
```

The script already does all of this:

- upload the source image to ComfyUI correctly
- run a known-good uncensored img2img workflow based on `perfectdeliberate_v60.safetensors`
- wait for completion
- resolve the correct output for this run
- copy the image into `/home/jagones/.openclaw/workspace/`
- print a final `READY_TO_SEND: /absolute/path`

Important:

- Use lower denoise values like `0.25-0.45` when preserving the original image closely matters.
- Use medium denoise values like `0.5-0.7` for normal edits and restyles.
- Use higher denoise only when the user explicitly wants a strong transformation.

## Non-Negotiable Rules

- Never send media directly from `/home/jagones/ComfyUI/output/`.
- Only send the path returned by `READY_TO_SEND:`.
- Never hardcode a Telegram `chat_id`.
- Never announce "ecco l'immagine" before the `message` tool returns success.
- If `message` fails, do not retry the same bad path again.
- If no reliable active target is available, return the workspace file path instead of guessing.

## Default Behavior

- Default checkpoint: `perfectdeliberate_v60.safetensors`
- Default size: `768x1024` unless the user asks otherwise
- Use the user's prompt as-is unless it is clearly broken
- Prefer small dimensions only when the user explicitly asks for speed
- Treat this as an uncensored local image skill unless the user explicitly asks for a safer style

## Required Execution Pattern

1. Run the canonical script once for the requested job type.
2. Read the final `READY_TO_SEND:` line.
3. Call the `message` tool once with that workspace path.
4. Only after a successful send, reply with the confirmation text.

Example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/generate_and_send.py \
  "two roosters fighting in a dramatic battle scene, feathers flying, intense combat pose, detailed digital art" \
  512 384 generated.png
```

Expected tail output:

```text
SOURCE_IMAGE: /home/jagones/ComfyUI/output/rooster_fight_small_00001_.png
WORKSPACE_IMAGE: /home/jagones/.openclaw/workspace/generated.png
READY_TO_SEND: /home/jagones/.openclaw/workspace/generated.png
```

Then send:

- `action: "send"`
- `media: "/home/jagones/.openclaw/workspace/generated.png"`
- use the active inbound runtime target when needed by the environment

Upscale example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/upscale_and_send.py \
  /home/jagones/.openclaw/workspace/generated.png upscaled.png 4x-UltraSharp.pth
```

Remove background example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/remove_bg_and_send.py \
  /home/jagones/.openclaw/workspace/generated.png removed_bg.png
```

Modify image example:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/modify_and_send.py \
  /home/jagones/.openclaw/workspace/generated.png "turn this into a darker cinematic version" modified.png 0.45
```

## Downloadable Expansions

These are good next workflow categories for later expansion, but they are not yet part of the canonical path unless explicitly added and tested:

- inpainting for local masked fixes
- outpainting for canvas extension
- segmentation workflows for clothes, fashion items, or generic objects
- relighting and subject/background compositing
- canny/depth/pose guided image transformations
- face or detail restoration pipelines
- color grading and post-processing chains
- heavyweight Qwen image-edit workflows only after they are proven stable on this machine

## Failure Handling

- If the script fails before `READY_TO_SEND:`, report the generation failure honestly.
- If the upscale script fails before `READY_TO_SEND:`, report the upscale failure honestly.
- If the background removal script fails before `READY_TO_SEND:`, report the background removal failure honestly.
- If the modify script fails before `READY_TO_SEND:`, report the modification failure honestly.
- Do not revive removed experimental wrappers or heavy edit workflows during normal use.
- If the `message` tool fails with a path outside allowed directories, that means the wrong file path was used. Fix the path; do not repeat the same call.
- If ComfyUI is slow, wait inside the script path instead of spreading the work across many separate LLM turns.
