#!/bin/bash
# Install API + UI (convenience wrapper)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
bash "$ROOT/install-api.sh" "$@"
bash "$ROOT/install-ui.sh" "$@"
