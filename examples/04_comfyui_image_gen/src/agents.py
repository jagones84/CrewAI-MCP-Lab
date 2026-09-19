"""Agents used by the ComfyUI image generation example.

A single agent (the *Visual Designer*) is reused across every operation:
text-to-image generation, img2img modification, upscaling, and background
removal. The agent receives the full ComfyUI MCP tool surface (or a
filtered subset) and follows the per-task rules defined in ``tasks.py``.
"""

from __future__ import annotations

from crewai import Agent, LLM
from typing import Any, List


class ImageGenAgents:
    """Factory for the visual designer agent used by example 04."""

    def __init__(self, llm: LLM) -> None:
        """Store the LLM that backs the agent."""
        self.llm = llm

    def visual_designer(self, tools: List[Any]) -> Agent:
        """Create the visual designer agent.

        Args:
            tools: List of MCP tools exposed by the ComfyUI server. The agent
                may receive ``generate_image``, ``modify_image``,
                ``upscale_image``, ``remove_background``, and
                ``list_workflows`` depending on the chosen pipeline.

        Returns:
            Configured :class:`crewai.Agent`.
        """
        return Agent(
            role="AI Visual Designer",
            goal=(
                "Produce, refine, and deliver high-quality images by orchestrating "
                "the ComfyUI MCP tools (generate, modify, upscale, remove background)."
            ),
            backstory=(
                "Expert prompt engineer for diffusion models. You write concise, vivid "
                "prompts that describe subject, composition, lighting, and style. You "
                "ALWAYS pass a full file path (not a directory) to any ComfyUI tool. "
                "When chaining operations you reuse the file path returned by the "
                "previous tool instead of inventing a new one. You never invent tool "
                "names: if a tool is not in your toolbox you tell the user it is missing."
            ),
            llm=self.llm,
            tools=tools,
            allow_delegation=False,
            verbose=True,
        )
