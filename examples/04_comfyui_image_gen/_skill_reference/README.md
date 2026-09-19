# Reference: openclaw comfyui-image-gen skill

This folder contains a verbatim snapshot of the openclaw skill
`Z:\.openclaw\workspace\skills\comfyui-image-gen` (home DGX: `jagones@DGX-SPARK-ETH`).

It is kept as **reference material** for the canonical patterns we
adopted in the CrewAI MCP server extension:

* upload a local image to ComfyUI via `/upload/image` (multipart);
* submit a known-good workflow from `workflow_files/`;
* wait for the queue to drain via WebSocket;
* resolve the produced image from `/history` and download it via `/view`;
* copy the result into a workspace folder the caller controls.

The CrewAI version differs from the openclaw one in two important ways:

1. **No Telegram `message` step.** The openclaw scripts print
   `READY_TO_SEND: <path>` because they pipe the result into a
   Telegram delivery tool. In CrewAI the tool result string is enough:
   the agent reads the returned path and can use it as the input to
   the next MCP tool call.
2. **Single-server entry point.** The openclaw skill wraps each job in
   a small shell script (`quick-*.sh`) so the LLM cannot accidentally
   rebuild the workflow by hand. In CrewAI we expose the same primitive
   directly as MCP tools (`generate_image`, `modify_image`,
   `upscale_image`, `remove_background`), so the agent chooses the
   right tool by name instead of by shell command.

Do not invoke the openclaw scripts directly from the CrewAI example:
they assume a Linux filesystem and the `jagones@DGX-SPARK-ETH` tunnel,
neither of which is portable to the Windows host where the example
runs.
