#!/bin/bash
# Verify proxmox-node-hw-ui installation.
set -euo pipefail

ERR=0
MGR_JS="/usr/share/pve-manager/js"
check() {
    if eval "$2"; then echo "OK: $1"; else echo "FAIL: $1"; ERR=1; fi
}

for f in pve_hw_core.js pve_hw_tab.js pve_hw_plugin.js pve_hw_build_info.js; do
    check "$f in mgr" "test -f $MGR_JS/$f"
    check "index.tpl $f" "grep -q $f /usr/share/pve-manager/index.html.tpl"
done

check "no legacy summary override" "! test -f $MGR_JS/pve_node_summary.js"
check "no legacy hardware bundle" "! test -f $MGR_JS/pve_node_hardware.js"
check "UI share dir" "test -d /usr/share/pve-node-hw-ui/ui"
check "plugin source" "test -f /usr/share/pve-node-hw-ui/ui/pve_hw_plugin.js"

if [[ "$ERR" -ne 0 ]]; then
    echo "UI verification failed. Run: bash install-ui.sh"
    exit 1
fi
echo "UI checks passed."
