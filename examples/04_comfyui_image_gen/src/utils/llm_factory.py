"""LLM factory that wires OpenRouter / OpenAI / Ollama / LlamaCpp configs to CrewAI."""

from __future__ import annotations

import os
from typing import Any

from crewai import LLM
from dotenv import load_dotenv

STALE_OPENROUTER_MODELS = {
    "google/gemini-2.0-flash-001": "google/gemini-2.5-flash-lite",
    "google/gemini-2.0-flash": "google/gemini-2.5-flash-lite",
}


def get_llm(config: dict[str, Any]) -> LLM:
    """Build a CrewAI ``LLM`` instance from the ``llm`` config section.

    Args:
        config: The ``llm`` mapping loaded from ``config/preferences.yaml``.

    Returns:
        A configured :class:`crewai.LLM` instance.
    """
    repo_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )
    load_dotenv(os.path.join(repo_root, ".env"), override=True)

    provider = (config.get("provider") or "openrouter").lower()
    temperature = float(config.get("temperature", 0.4))
    provider_cfg = config.get(provider, {}) or {}
    model = provider_cfg.get("model") or config.get("model") or "google/gemini-2.5-flash-lite"

    if provider == "openrouter":
        model = os.environ.get("OPENROUTER_MODEL") or model
        model = STALE_OPENROUTER_MODELS.get(model, model)
        if not model.startswith("openrouter/"):
            model = f"openrouter/{model}"
        api_key = os.environ.get("OPENROUTER_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if api_key and not os.environ.get("OPENROUTER_API_KEY"):
            os.environ["OPENROUTER_API_KEY"] = api_key
        os.environ.pop("OPENAI_API_BASE", None)
        return LLM(model=model, api_key=api_key, temperature=temperature)

    if provider == "openai":
        return LLM(
            model=model,
            api_key=os.environ.get("OPENAI_API_KEY"),
            temperature=temperature,
        )

    if provider == "ollama":
        base_url = provider_cfg.get("base_url") or "http://localhost:11434/v1"
        os.environ.pop("OPENAI_API_BASE", None)
        return LLM(
            model=f"ollama/{model}",
            api_key="NA",
            base_url=base_url,
            temperature=temperature,
        )

    if provider == "llamacpp":
        base_url = provider_cfg.get("base_url") or "http://localhost:8080/v1"
        return LLM(
            model=f"openai/{model}",
            api_key="EMPTY",
            base_url=base_url,
            temperature=temperature,
        )

    # Fallback: pass-through model string, let CrewAI negotiate.
    return LLM(model=model, temperature=temperature)
