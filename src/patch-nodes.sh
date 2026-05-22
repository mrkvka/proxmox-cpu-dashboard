#!/bin/bash
# Register native hardware API on PVE::API2::Nodes::Nodeinfo (/nodes/{node}/hw*).
set -euo pipefail

FILE="/usr/share/perl5/PVE/API2/Nodes.pm"
HW_PM="/usr/share/perl5/PVE/API2/Nodes/Hardware.pm"
MARKER_BEGIN="# PVE-HW-DASHBOARD: begin"
MARKER_END="# PVE-HW-DASHBOARD: end"

if [ ! -f "$FILE" ] || [ ! -f "$HW_PM" ]; then
    echo "ERROR: missing $FILE or $HW_PM"
    exit 1
fi

perl -i -0777 -pe 's/\n# PVE CPU Dashboard native hardware API.*?(\npackage PVE::API2::Nodes;\n)/$1/s' "$FILE" 2>/dev/null || true
perl -i -0777 -pe 's/\n# CPU Frequency control endpoint.*?\n\}\);\n//s' "$FILE" 2>/dev/null || true
perl -i -0777 -pe 's/\n# PVE-HW-DASHBOARD: begin.*?\n# PVE-HW-DASHBOARD: end\n//s' "$FILE" 2>/dev/null || true

if ! grep -qF "$MARKER_BEGIN" "$FILE"; then
    python3 - "$FILE" "$MARKER_BEGIN" "$MARKER_END" <<'PY'
import sys
path, begin, end = sys.argv[1:4]
text = open(path, encoding="utf-8").read()
block = f"\n{begin}\nuse PVE::API2::Nodes::Hardware;\nPVE::API2::Nodes::Hardware::register_api();\n{end}\n"
needle = "\npackage PVE::API2::Nodes;\n"
if needle not in text:
    raise SystemExit("package PVE::API2::Nodes; not found")
text = text.replace(needle, block + needle, 1)
open(path, "w", encoding="utf-8").write(text)
PY
fi

perl -c "$FILE"
echo "Nodes.pm OK: /nodes/{node}/hw* on Nodeinfo"
grep -qF 'PVE::API2::Nodes::Hardware::register_api' "$FILE"
