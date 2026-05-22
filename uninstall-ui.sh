#!/bin/bash
# Remove proxmox-node-hw-ui only (keeps API)
set -euo pipefail

SHARE_UI="/usr/share/pve-node-hw-ui"
INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
MGR_JS="/usr/share/pve-manager/js"
INDEX_BAK=$(ls -t /usr/share/pve-manager/index.html.tpl.bak_* 2>/dev/null | head -1)

ALL_SCRIPTS=(pve_hw_core.js pve_hw_tab.js pve_hw_plugin.js pve_hw_build_info.js pve_node_summary.js pve_node_hardware.js)

echo "=========================================="
echo " Uninstall proxmox-node-hw-ui"
echo "=========================================="

if [[ -n "$INDEX_BAK" && -f "$INDEX_BAK" ]]; then
    cp "$INDEX_BAK" "$INDEX_TPL"
    echo "[*] Restored index.html.tpl"
else
    for f in "${ALL_SCRIPTS[@]}"; do
        sed -i "\\|/pve2/js/${f}|d" "$INDEX_TPL"
        rm -f "$MGR_JS/$f"
    done
fi

for f in "${ALL_SCRIPTS[@]}"; do
    rm -f "$MGR_JS/$f"
done
rm -rf "$SHARE_UI"

systemctl restart pveproxy
echo " Done. API remains active."
