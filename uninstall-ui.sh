#!/bin/bash
# Remove proxmox-node-hw-ui only (keeps API)
set -euo pipefail

SHARE_UI="/usr/share/pve-node-hw-ui"
INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
INDEX_BAK=$(ls -t /usr/share/pve-manager/index.html.tpl.bak_* 2>/dev/null | head -1)

echo "=========================================="
echo " Uninstall proxmox-node-hw-ui"
echo "=========================================="

if [[ -n "$INDEX_BAK" && -f "$INDEX_BAK" ]]; then
    cp "$INDEX_BAK" "$INDEX_TPL"
    echo "[*] Restored index.html.tpl"
else
    sed -i '\|/pve2/js/pve_node_summary.js|d' "$INDEX_TPL"
    sed -i '\|/pve2/js/pve_node_hardware.js|d' "$INDEX_TPL"
fi

rm -f /usr/share/pve-manager/js/pve_node_summary.js
rm -f /usr/share/pve-manager/js/pve_node_hardware.js
rm -rf "$SHARE_UI"

systemctl restart pveproxy
echo " Done. API remains active."
