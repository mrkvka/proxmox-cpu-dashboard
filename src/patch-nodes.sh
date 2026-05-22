#!/bin/bash
# Register native hardware API in PVE::API2::Nodes (no thermalstate mutation).
set -euo pipefail

FILE="/usr/share/perl5/PVE/API2/Nodes.pm"
HW_PM="/usr/share/perl5/PVE/API2/Nodes/Hardware.pm"
MARKER_BEGIN="# PVE-HW-DASHBOARD: begin"
MARKER_END="# PVE-HW-DASHBOARD: end"

if [ ! -f "$FILE" ]; then
    echo "ERROR: $FILE not found — is this a Proxmox VE host?"
    exit 1
fi

if [ ! -f "$HW_PM" ]; then
    echo "ERROR: $HW_PM missing — run install.sh first."
    exit 1
fi

# Remove legacy inline patches from older dashboard versions
perl -i -0777 -pe 's/\n# PVE CPU Dashboard native hardware API.*?(\npackage PVE::API2::Nodes;\n)/$1/s' "$FILE" 2>/dev/null || true
perl -i -0777 -pe 's/\n# CPU Frequency control endpoint.*?\n\}\);\n//s' "$FILE" 2>/dev/null || true
perl -i -0777 -pe 's/\n# PVE-HW-DASHBOARD: begin.*?\n# PVE-HW-DASHBOARD: end\n//s' "$FILE" 2>/dev/null || true

# Register after Nodes.pm is fully loaded (append before final "1;")
if ! grep -qF "$MARKER_BEGIN" "$FILE"; then
    perl -i -pe '
        if (/^1;\s*$/ && !$done) {
            print "'"$MARKER_BEGIN"'\n";
            print "use PVE::API2::Nodes::Hardware;\n";
            print "PVE::API2::Nodes::Hardware::register_api();\n";
            print "'"$MARKER_END"'\n";
            $done = 1;
        }
    ' "$FILE"
fi

perl -c "$FILE"
echo "Nodes.pm OK: hardware API via PVE::API2::Nodes::Hardware"
grep -qF 'PVE::API2::Nodes::Hardware::register_api' "$FILE"
