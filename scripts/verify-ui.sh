#!/bin/bash
# Verify proxmox-node-hw-ui installation.
set -euo pipefail

ERR=0
check() {
    if eval "$2"; then echo "OK: $1"; else echo "FAIL: $1"; ERR=1; fi
}

check "summary JS" "test -f /usr/share/pve-manager/js/pve_node_summary.js"
check "hardware JS" "test -f /usr/share/pve-manager/js/pve_node_hardware.js"
check "index.tpl summary" "grep -q pve_node_summary.js /usr/share/pve-manager/index.html.tpl"
check "index.tpl hardware" "grep -q pve_node_hardware.js /usr/share/pve-manager/index.html.tpl"
check "build info JS" "test -f /usr/share/pve-manager/js/pve_hw_build_info.js"
check "index build info" "grep -q pve_hw_build_info.js /usr/share/pve-manager/index.html.tpl"
check "UI share dir" "test -d /usr/share/pve-node-hw-ui"

if [[ "$ERR" -ne 0 ]]; then
    echo "UI verification failed. Run: bash install-ui.sh"
    exit 1
fi
echo "UI checks passed."
