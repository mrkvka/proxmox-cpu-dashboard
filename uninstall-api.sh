#!/bin/bash
# Remove proxmox-node-hw-api (run uninstall-ui.sh first if UI is installed)
set -euo pipefail

SHARE_DIR="/usr/share/pve-node-hw-api"

echo "=========================================="
echo " Uninstall proxmox-node-hw-api"
echo "=========================================="

if [[ -f /usr/share/pve-manager/index.html.tpl ]] && \
   grep -q 'pve_node_hardware.js' /usr/share/pve-manager/index.html.tpl 2>/dev/null; then
    echo "ERROR: UI still installed. Run: bash uninstall-ui.sh"
    exit 1
fi

NODES_PM="/usr/share/perl5/PVE/API2/Nodes.pm"
NODES_BAK=$(ls -t /usr/share/perl5/PVE/API2/Nodes.pm.bak_* 2>/dev/null | head -1)

if [[ -n "$NODES_BAK" && -f "$NODES_BAK" ]]; then
    cp "$NODES_BAK" "$NODES_PM"
    echo "[*] Restored Nodes.pm from $(basename "$NODES_BAK")"
elif grep -qF 'PVE-HW-DASHBOARD: begin' "$NODES_PM" 2>/dev/null; then
    perl -i -0777 -pe 's/\n# PVE-HW-DASHBOARD: begin.*?\n# PVE-HW-DASHBOARD: end\n//s' "$NODES_PM"
    echo "[*] Stripped API hook from Nodes.pm"
fi

rm -f /usr/share/perl5/PVE/API2/Nodes/Hardware.pm
rm -f /usr/local/bin/pve-hw-collect.py /usr/local/bin/pve-hw-apply.py
rm -f /usr/local/bin/pve-cpufreq-set.sh /usr/local/bin/pve-cpus-set.sh
rm -rf /var/cache/pve-hw-dashboard
rm -rf "$SHARE_DIR"

perl -c "$NODES_PM" 2>/dev/null && echo "[*] Nodes.pm OK"
systemctl restart pvedaemon pveproxy
echo " Done."
