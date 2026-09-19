# ComfyUI Image Creation And Processing Skill

This is the single ComfyUI image skill.

It covers:

- text-to-image generation
- image upscaling
- background removal
- image-to-image modification

Both paths are intentionally reduced to one canonical wrapper each to avoid multi-step LLM mistakes.

## Canonical Command

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/generate_and_send.py \
  "your prompt here" 1024 1024 generated.png
```

Optional wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-gen.sh \
  "your prompt here" 1024 1024 generated.png
```

## What The Script Guarantees

- submits the job to local ComfyUI
- waits for completion
- resolves the output file for the current run
- copies it into `/home/jagones/.openclaw/workspace/`
- prints `READY_TO_SEND: /absolute/path`

## Upscaling Path

Upscaling does not use `generate_and_send.py`.

Use the dedicated canonical script instead:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/upscale_and_send.py \
  /absolute/source/image.png upscaled.png 4x-UltraSharp.pth
```

Optional wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-upscale.sh \
  /absolute/source/image.png upscaled.png 4x-UltraSharp.pth
```

The upscale script:

- uploads the source image to ComfyUI correctly
- runs a known-good `LoadImage -> UpscaleModelLoader -> ImageUpscaleWithModel -> SaveImage` workflow
- waits for completion
- copies the final output into `/home/jagones/.openclaw/workspace/`
- prints `READY_TO_SEND: /absolute/path`

For quality-first upscales, prefer `4x-UltraSharp.pth`.

## Background Removal Path

Use the dedicated canonical script instead:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/remove_bg_and_send.py \
  /absolute/source/image.png removed_bg.png
```

Optional wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-remove-bg.sh \
  /absolute/source/image.png removed_bg.png
```

The background removal script:

- uploads the source image to ComfyUI correctly
- runs a known-good `LoadImage -> LayerMask: RemBgUltra -> SaveImage` workflow
- waits for completion
- copies the final output into `/home/jagones/.openclaw/workspace/`
- prints `READY_TO_SEND: /absolute/path`

This path uses the installed `ComfyUI_LayerStyle` node family.

## Image Modification Path

Use the dedicated canonical script instead:

```bash
python3 /home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/modify_and_send.py \
  /absolute/source/image.png "your edit prompt" modified.png 0.55
```

Optional wrapper:

```bash
/home/jagones/.openclaw/workspace/skills/comfyui-image-gen/scripts/quick-modify.sh \
  /absolute/source/image.png "your edit prompt" modified.png 0.55
```

The image modification script:

- uploads the source image to ComfyUI correctly
- runs a known-good uncensored img2img workflow with `perfectdeliberate_v60.safetensors`
- waits for completion
- copies the final output into `/home/jagones/.openclaw/workspace/`
- prints `READY_TO_SEND: /absolute/path`

Denoise guidance:

- `0.25-0.45`: preserve most of the original image
- `0.5-0.7`: normal restyle/edit
- `0.75+`: strong transformation only when explicitly wanted

## Expandable Workflow Ideas

Good future additions for this skill family:

- inpainting
- outpainting
- segmentation by clothes/object
- relighting
- pose/depth/canny guided edits
- face/detail restoration
- color grading/post-processing chains
- heavyweight Qwen image-edit pipelines only after they are stable under repeated local runs

## Delivery Rule

Never send media from `/home/jagones/ComfyUI/output/`.

Only send the exact workspace path returned by `READY_TO_SEND:`.

## Typical Use

1. Run the canonical command once.
2. Parse the `READY_TO_SEND:` line.
3. Call the `message` tool with that workspace file.
4. Only after `message` succeeds, send the human-facing confirmation text.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ComfyUI not responding` | Verify ComfyUI is running on `http://127.0.0.1:8188` |
| `READY_TO_SEND` missing | Treat the run as failed and report the error honestly |
| `OutboundDeliveryError` | You used the wrong path; send the workspace copy instead |
| Wrong image selected | Use the canonical script only; do not manually pick latest files |
| Upscale validation fails | Check that the selected upscale model exists in `ComfyUI/models/upscale_models/` |
| Agent looks for MCP upscale tools | Ignore that path and use `upscale_and_send.py` instead |
| Background removal fails on first run | Check the RMBG model is present under `ComfyUI/models/rmbg/RMBG-1.4/` |
| Image modification is too strong | Lower the denoise value in `modify_and_send.py` or `quick-modify.sh` |
| A heavy experimental workflow kills ComfyUI | Remove it from the canonical path and fall back to the stable wrappers only |
