#!/usr/bin/env bash
# via54Larkgroups Linux/macOS wrapper
# Usage: feishu-vault <command> [args...]
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$HERE")"
PYTHON="${PYTHON:-python3}"
exec "$PYTHON" -m via54_larkgroups "$@"