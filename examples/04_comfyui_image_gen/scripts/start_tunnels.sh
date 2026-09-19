#!/usr/bin/env bash
# ============================================================================
# Open DGX Spark tunnels required by example 04 (ComfyUI image generation).
# Edit REMOTE_USER / REMOTE_HOST below to match your environment.
# ============================================================================

set -e

REMOTE_USER="${REMOTE_USER:-jagones}"
REMOTE_HOST="${REMOTE_HOST:-DGX-SPARK-ETH}"

# ComfyUI: local 11002 -> remote 8188 (DGX Spark ComfyUI)
ssh -L 11002:localhost:8188 "${REMOTE_USER}@${REMOTE_HOST}" -N &

# Optional: LLM tunnel if you also want to point example 04 at the DGX llama.cpp server.
# Uncomment to enable.
# ssh -L 11003:localhost:8092 "${REMOTE_USER}@${REMOTE_HOST}" -N &

echo "DGX Spark tunnels for example 04 are now active (ComfyUI on local 11002)."
echo "Press Ctrl-C to stop."

wait
