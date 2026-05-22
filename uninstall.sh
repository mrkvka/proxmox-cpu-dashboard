#!/bin/bash
# Remove UI then API (convenience wrapper)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
bash "$ROOT/uninstall-ui.sh" 2>/dev/null || true
bash "$ROOT/uninstall-api.sh"
