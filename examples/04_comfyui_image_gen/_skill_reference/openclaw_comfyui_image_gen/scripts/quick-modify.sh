#!/bin/bash
# Canonical wrapper for ComfyUI image modification.
# Usage: quick-modify.sh /absolute/source/image "prompt" [output_name] [denoise_strength]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/modify_and_send.py" \
  "${1:?source image path required}" \
  "${2:?prompt required}" \
  "${3:-modified.png}" \
  "${4:-0.55}"
