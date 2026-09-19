"""Task definitions for the ComfyUI image generation example.

Two operating modes are supported:

* ``generate_image``     — single-shot text-to-image (default).
* ``full_pipeline``      — generate -> modify -> upscale, with an optional
                           background-removal branch on the original.

Each task is intentionally explicit about the tool name to call and the
arguments to pass, so the LLM cannot invent ad-hoc shell pipelines the way
the openclaw ``comfyui-image-gen`` skill used to (the skill enforced a
single canonical command per job; we enforce the same with strict
description templates).
"""

from __future__ import annotations

from crewai import Agent, Task
from typing import List, Optional


class ImageGenTasks:
    """Factory for image-generation tasks."""

    def generate_image(
        self,
        agent: Agent,
        prompt: str,
        negative_prompt: str,
        seed: int,
        workflow: str,
        output_path: str,
    ) -> Task:
        """Create the single image-generation task.

        Args:
            agent: The visual designer agent.
            prompt: Positive prompt.
            negative_prompt: Negative prompt.
            seed: Deterministic seed (use ``-1`` to randomize).
            workflow: ComfyUI workflow name to invoke.
            output_path: Absolute *file* path where the generated image must be saved.

        Returns:
            Configured :class:`crewai.Task`.
        """
        description = f"""
You are generating a single concept image with the ComfyUI MCP tool.

Brief:
{prompt}

Negative prompt:
{negative_prompt}

Hard rules (read carefully):
1. Use the `generate_image` tool exposed by the ComfyUI MCP server.
2. Pass the workflow name exactly: '{workflow}'.
3. Pass the seed value: {seed}.
4. Pass the full output FILE path (not a directory):
   '{output_path}'
5. Do NOT invent new tool names. If the tool response contains a file path, return it.
6. Do NOT wrap the output path in quotes inside the tool arguments.
""".strip()

        return Task(
            description=description,
            expected_output=(
                "The full file path of the generated image and a one-sentence description of the visual."
            ),
            agent=agent,
        )

    def modify_image(
        self,
        agent: Agent,
        source_path: str,
        edit_prompt: str,
        output_path: str,
        denoise: float = 0.55,
        negative_prompt: str = "",
        workflow_name: str = "img2img_workflow.json",
    ) -> Task:
        """Create an img2img modification task that reuses ``source_path``."""
        description = f"""
You are refining an existing image with the ComfyUI `modify_image` MCP tool.

Source image (read-only, do NOT modify in place):
{source_path}

Edit instructions (positive prompt for the diffusion model):
{edit_prompt}

Negative prompt (leave empty to use the workflow default):
{negative_prompt}

Denoise strength ({denoise}):
* 0.25-0.45 -> preserve the original composition
* 0.5-0.7   -> normal restyle / edit
* 0.75+     -> strong transformation

Hard rules:
1. Use the `modify_image` tool exposed by the ComfyUI MCP server.
2. Pass the source FILE path exactly: '{source_path}'.
3. Pass the full output FILE path (not a directory): '{output_path}'.
4. Pass denoise as a number between 0.0 and 1.0: {denoise}.
5. Pass the workflow name: '{workflow_name}'.
6. Do NOT invent tool names. Do NOT pre-process the image with Python.
""".strip()
        return Task(
            description=description,
            expected_output=(
                "The full file path of the modified image and a one-sentence description of what changed."
            ),
            agent=agent,
        )

    def upscale_image(
        self,
        agent: Agent,
        source_path: str,
        output_path: str,
        model_name: str = "4x-UltraSharp.pth",
    ) -> Task:
        """Create an upscale task that doubles (or quadruples) ``source_path``."""
        description = f"""
You are upscaling an existing image with the ComfyUI `upscale_image` MCP tool.

Source image (read-only):
{source_path}

Upscale model to use:
{model_name}

Hard rules:
1. Use the `upscale_image` tool exposed by the ComfyUI MCP server.
2. Pass the source FILE path exactly: '{source_path}'.
3. Pass the full output FILE path (not a directory): '{output_path}'.
4. Pass the upscale model name: '{model_name}'.
5. Do NOT invent tool names. Do NOT run shell commands.
""".strip()
        return Task(
            description=description,
            expected_output=(
                "The full file path of the upscaled image and a one-sentence note about the resolution increase."
            ),
            agent=agent,
        )

    def remove_background(
        self,
        agent: Agent,
        source_path: str,
        output_path: str,
        model: str = "RMBG-2.0",
    ) -> Task:
        """Create a background-removal task."""
        description = f"""
You are removing the background of an existing image with the ComfyUI
`remove_background` MCP tool.

Source image (read-only):
{source_path}

Background-removal model:
{model}

Hard rules:
1. Use the `remove_background` tool exposed by the ComfyUI MCP server.
2. Pass the source FILE path exactly: '{source_path}'.
3. Pass the full output FILE path (not a directory): '{output_path}'.
4. Pass the model name: '{model}'.
5. Do NOT invent tool names.
""".strip()
        return Task(
            description=description,
            expected_output=(
                "The full file path of the background-removed image and a one-sentence description of what was kept."
            ),
            agent=agent,
        )

    def build_full_pipeline(
        self,
        agent: Agent,
        prompt: str,
        negative_prompt: str,
        seed: int,
        workflow: str,
        generated_path: str,
        edit_prompt: str,
        denoise: float,
        modified_path: str,
        upscale_model: str,
        upscaled_path: str,
        also_remove_background: bool = False,
        bg_removed_path: Optional[str] = None,
        bg_model: str = "RMBG-2.0",
    ) -> List[Task]:
        """Build the ordered list of tasks for the ``full`` pipeline.

        Order:
            1. generate_image -> ``generated_path``
            2. modify_image   -> ``modified_path``  (uses generated_path)
            3. upscale_image  -> ``upscaled_path``  (uses modified_path)
            4. remove_background -> ``bg_removed_path`` (uses generated_path)
               only when ``also_remove_background`` is True.

        Returns:
            A list of :class:`crewai.Task` ready to be wired into a
            :class:`crewai.Crew` with ``Process.sequential``.
        """
        tasks: List[Task] = [
            self.generate_image(
                agent=agent,
                prompt=prompt,
                negative_prompt=negative_prompt,
                seed=seed,
                workflow=workflow,
                output_path=generated_path,
            ),
            self.modify_image(
                agent=agent,
                source_path=generated_path,
                edit_prompt=edit_prompt,
                output_path=modified_path,
                denoise=denoise,
                negative_prompt=negative_prompt,
            ),
            self.upscale_image(
                agent=agent,
                source_path=modified_path,
                output_path=upscaled_path,
                model_name=upscale_model,
            ),
        ]
        if also_remove_background:
            if not bg_removed_path:
                raise ValueError(
                    "also_remove_background=True requires bg_removed_path to be set"
                )
            tasks.append(
                self.remove_background(
                    agent=agent,
                    source_path=generated_path,
                    output_path=bg_removed_path,
                    model=bg_model,
                )
            )
        return tasks
