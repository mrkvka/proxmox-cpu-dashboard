#!/bin/bash
# Build both .deb packages (API + UI).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
bash "$ROOT/scripts/build-deb-api.sh"
bash "$ROOT/scripts/build-deb-ui.sh"
echo "All packages in $ROOT/dist/"
