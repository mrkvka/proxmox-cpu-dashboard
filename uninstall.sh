#!/bin/bash
# Proxmox CPU Dashboard — full uninstall
set -euo pipefail

echo "=========================================="
echo " Proxmox CPU Dashboard — Uninstaller"
echo "=========================================="

NODES_PM="/usr/share/perl5/PVE/API2/Nodes.pm"
INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
NODES_BAK=$(ls -t /usr/share/perl5/PVE/API2/Nodes.pm.bak_* 2>/dev/null | head -1)
INDEX_BAK=$(ls -t /usr/share/pve-manager/index.html.tpl.bak_* 2>/dev/null | head -1)

restore_nodes_pm() {
    if [ -n "$NODES_BAK" ] && [ -f "$NODES_BAK" ]; then
        echo "[*] Restoring Nodes.pm from $(basename "$NODES_BAK")..."
        cp "$NODES_BAK" "$NODES_PM"
        return 0
    fi
    if [ -f "$NODES_PM" ] && grep -qF 'PVE-HW-DASHBOARD: begin' "$NODES_PM"; then
        echo "[*] Stripping API hook from Nodes.pm (no backup found)..."
        perl -i -0777 -pe 's/\n# PVE-HW-DASHBOARD: begin.*?\n# PVE-HW-DASHBOARD: end\n//s' "$NODES_PM"
        perl -i -0777 -pe 's/\n# PVE CPU Dashboard native hardware API.*?\n(?=package PVE::API2::Nodes;\n)//s' "$NODES_PM" 2>/dev/null || true
        return 0
    fi
    echo "WARNING: Could not restore Nodes.pm — check $NODES_PM manually"
    return 1
}

restore_index_tpl() {
    if [ -n "$INDEX_BAK" ] && [ -f "$INDEX_BAK" ]; then
        echo "[*] Restoring index.html.tpl from $(basename "$INDEX_BAK")..."
        cp "$INDEX_BAK" "$INDEX_TPL"
        return 0
    fi
    if [ -f "$INDEX_TPL" ]; then
        echo "[*] Removing dashboard script tags from index.html.tpl..."
        sed -i '\|/pve2/js/pve_node_summary.js|d' "$INDEX_TPL"
        sed -i '\|/pve2/js/pve_node_hardware.js|d' "$INDEX_TPL"
    fi
}

restore_nodes_pm
restore_index_tpl

echo "[*] Removing installed files..."
rm -f /usr/share/pve-manager/js/pve_node_summary.js
rm -f /usr/share/pve-manager/js/pve_node_hardware.js
rm -f /usr/share/perl5/PVE/API2/Nodes/Hardware.pm
rm -f /usr/local/bin/pve-hw-collect.py
rm -f /usr/local/bin/pve-hw-apply.py
rm -f /usr/local/bin/pve-hwinfo.sh
rm -f /usr/local/bin/pve-cpufreq-set.sh
rm -f /usr/local/bin/pve-cpus-set.sh
rm -f /usr/local/bin/pve-cpufreq-api.py
rm -rf /var/cache/pve-hw-dashboard

systemctl disable --now pve-cpufreq-api.service 2>/dev/null || true
rm -f /etc/systemd/system/pve-cpufreq-api.service
systemctl daemon-reload 2>/dev/null || true

if [ -f "$NODES_PM" ]; then
    perl -c "$NODES_PM" && echo "[*] Nodes.pm syntax OK"
fi

echo "[*] Restarting pvedaemon + pveproxy..."
systemctl restart pvedaemon pveproxy

echo ""
echo " Done. Hard-refresh the browser (Ctrl+Shift+R)."
echo " Backups kept as *.bak_* in /usr/share/perl5/PVE/API2/ and pve-manager/"
