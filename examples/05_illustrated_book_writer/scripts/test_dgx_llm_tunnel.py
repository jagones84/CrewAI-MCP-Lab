"""Preflight check for the DGX LLM tunnel used by example 05."""

from __future__ import annotations

import json
import os
import sys
from typing import Any
from urllib import error, request


BASE_ROOT_URL = os.getenv("DGX_LLM_BASE_URL", "http://localhost:11003")
MODEL_NAME = os.getenv("DGX_LLM_MODEL", "qwen-3.6-35b-a3b-claude47-opus-abliterated")
MODELS_URL = f"{BASE_ROOT_URL}/v1/models"
CHAT_COMPLETIONS_URL = f"{BASE_ROOT_URL}/v1/chat/completions"


def fetch_models() -> dict[str, Any]:
    """Fetch the model list from the tunneled OpenAI-compatible endpoint."""
    with request.urlopen(MODELS_URL, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def tiny_chat() -> dict[str, Any]:
    """Issue a tiny chat completion to confirm the tunnel is serving requests."""
    payload = json.dumps(
        {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Reply with OK only."}],
            "max_tokens": 8,
            "temperature": 0.0,
        }
    ).encode("utf-8")
    req = request.Request(
        CHAT_COMPLETIONS_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer EMPTY",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    """Run the DGX tunnel preflight and print both JSON responses."""
    try:
        print(json.dumps(fetch_models(), indent=2))
        print(json.dumps(tiny_chat(), indent=2))
        return 0
    except error.URLError as exc:
        print(
            "DGX tunnel preflight failed: "
            f"{exc}. Verify scripts\\start_tunnels.bat and the remote llama.cpp server."
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
