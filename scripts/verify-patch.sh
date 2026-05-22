#!/bin/bash
# Post-install verification for PVE hardware dashboard.
set -euo pipefail

NODES_PM="/usr/share/perl5/PVE/API2/Nodes.pm"
HW_PM="/usr/share/perl5/PVE/API2/Nodes/Hardware.pm"
ERR=0

check() {
    if eval "$2"; then
        echo "OK: $1"
    else
        echo "FAIL: $1"
        ERR=1
    fi
}

check "Nodes.pm syntax" "perl -c '$NODES_PM' >/dev/null 2>&1"
check "Hardware.pm installed" "test -f '$HW_PM'"
check "API hook in Nodes.pm" "grep -qF 'PVE-HW-DASHBOARD: begin' '$NODES_PM'"
check "collector binary" "test -x /usr/local/bin/pve-hw-collect.py"
check "apply binary" "test -x /usr/local/bin/pve-hw-apply.py"
check "UI summary JS" "test -f /usr/share/pve-manager/js/pve_node_summary.js"
check "UI hardware JS" "test -f /usr/share/pve-manager/js/pve_node_hardware.js"

if command -v pvesh >/dev/null 2>&1; then
    NODE=$(hostname -s 2>/dev/null || hostname)
    if pvesh get "/nodes/${NODE}/hw" --output-format json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('meta',{}).get('version') else 1)" 2>/dev/null; then
        echo "OK: GET /nodes/${NODE}/hw"
    else
        echo "WARN: GET /nodes/${NODE}/hw failed (check Sys.Audit / pvedaemon)"
        ERR=1
    fi
fi

if [ "$ERR" -ne 0 ]; then
    echo ""
    echo "Verification failed. Try: bash install.sh"
    exit 1
fi

echo ""
echo "All checks passed."
exit 0
