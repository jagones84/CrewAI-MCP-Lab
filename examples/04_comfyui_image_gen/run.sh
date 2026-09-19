#!/usr/bin/env bash
# Convenience launcher for example 04.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${SCRIPT_DIR}/src:${SCRIPT_DIR}/../../src:${PYTHONPATH:-}"
python "${SCRIPT_DIR}/src/main.py"
