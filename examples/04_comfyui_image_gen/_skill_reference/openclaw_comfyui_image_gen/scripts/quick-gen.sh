#!/bin/bash
# Canonical wrapper for the ComfyUI skill.
# Usage: quick-gen.sh "prompt" [width] [height] [output_name]

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

exec python3 "$SCRIPT_DIR/generate_and_send.py" \
  "${1:-A beautiful landscape}" \
  "${2:-1024}" \
  "${3:-1024}" \
  "${4:-generated.png}"
