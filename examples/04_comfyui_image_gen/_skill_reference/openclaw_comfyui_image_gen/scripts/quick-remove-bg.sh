#!/bin/bash
# Canonical wrapper for ComfyUI background removal.
# Usage: quick-remove-bg.sh /absolute/source/image [output_name]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/remove_bg_and_send.py" \
  "${1:?source image path required}" \
  "${2:-removed_bg.png}"
