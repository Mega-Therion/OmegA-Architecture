#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RENDERER="$ROOT_DIR/scripts/render_publication_exports.py"

if [[ "$#" -eq 0 ]]; then
  exec python3 "$RENDERER" --all
fi

exec python3 "$RENDERER" "$@"
