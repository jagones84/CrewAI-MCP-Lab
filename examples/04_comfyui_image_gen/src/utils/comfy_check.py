"""Lightweight ComfyUI HTTP pre-flight check."""

from __future__ import annotations

import logging
import socket

logger = logging.getLogger(__name__)


def check_comfyui_connection(host: str = "127.0.0.1", port: int = 8188, timeout: float = 2.0) -> bool:
    """Return True if a TCP connection to the ComfyUI host:port succeeds.

    Args:
        host: ComfyUI host.
        port: ComfyUI port.
        timeout: Connection timeout in seconds.

    Returns:
        True when the endpoint accepts a TCP connection, False otherwise.
    """
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, ConnectionRefusedError, OSError) as exc:
        logger.debug("ComfyUI not reachable at %s:%s (%s)", host, port, exc)
        return False
