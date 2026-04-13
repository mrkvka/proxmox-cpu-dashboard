#!/bin/bash
# Proxmox CPU Dashboard - Uninstaller
set -e

echo "=========================================="
echo " Proxmox CPU Dashboard - Uninstaller"
echo "=========================================="

# Find latest backup
NODES_BAK=$(ls -t /usr/share/perl5/PVE/API2/Nodes.pm.bak_* 2>/dev/null | head -1)
INDEX_BAK=$(ls -t /usr/share/pve-manager/index.html.tpl.bak_* 2>/dev/null | head -1)

if [ -z "$NODES_BAK" ] || [ -z "$INDEX_BAK" ]; then
    echo "ERROR: No backup files found. Cannot restore."
    echo "  Nodes.pm backup: ${NODES_BAK:-NOT FOUND}"
    echo "  index.html.tpl backup: ${INDEX_BAK:-NOT FOUND}"
    exit 1
fi

echo "[*] Restoring Nodes.pm from: $NODES_BAK"
cp "$NODES_BAK" /usr/share/perl5/PVE/API2/Nodes.pm

echo "[*] Restoring index.html.tpl from: $INDEX_BAK"
cp "$INDEX_BAK" /usr/share/pve-manager/index.html.tpl

echo "[*] Removing JS override..."
rm -f /usr/share/pve-manager/js/pve_node_summary.js

echo "[*] Removing helper scripts..."
rm -f /usr/local/bin/pve-hwinfo.sh
rm -f /usr/local/bin/pve-cpufreq-set.sh

echo "[*] Restarting pveproxy..."
systemctl restart pveproxy

echo ""
echo "=========================================="
echo " Uninstall complete!"
echo "=========================================="
echo " Press Ctrl+Shift+R in browser to force reload."
echo ""
