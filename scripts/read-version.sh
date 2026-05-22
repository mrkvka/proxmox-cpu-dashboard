#!/bin/bash
# Print package version from repo root VERSION file.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
tr -d '[:space:]' < "$ROOT/VERSION"
