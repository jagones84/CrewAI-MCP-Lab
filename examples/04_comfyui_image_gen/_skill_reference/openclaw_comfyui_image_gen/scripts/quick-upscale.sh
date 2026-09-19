#!/bin/bash
# Canonical wrapper for ComfyUI upscaling.
# Usage: quick-upscale.sh /absolute/source/image [output_name] [upscale_model]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/upscale_and_send.py" \
  "${1:?source image path required}" \
  "${2:-upscaled.png}" \
  "${3:-4x-UltraSharp.pth}"
