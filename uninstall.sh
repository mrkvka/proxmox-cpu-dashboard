#!/bin/bash
# Proxmox CPU Dashboard v2 — Uninstaller
set -euo pipefail

echo "=========================================="
echo " Proxmox CPU Dashboard v2 — Uninstaller"
echo "=========================================="

NODES_BAK=$(ls -t /usr/share/perl5/PVE/API2/Nodes.pm.bak_* 2>/dev/null | head -1)
INDEX_BAK=$(ls -t /usr/share/pve-manager/index.html.tpl.bak_* 2>/dev/null | head -1)

if [ -z "$NODES_BAK" ] || [ -z "$INDEX_BAK" ]; then
    echo "ERROR: No backup files found."
    exit 1
fi

cp "$NODES_BAK" /usr/share/perl5/PVE/API2/Nodes.pm
cp "$INDEX_BAK" /usr/share/pve-manager/index.html.tpl
rm -f /usr/share/pve-manager/js/pve_node_summary.js

rm -f /usr/local/bin/pve-hw-collect.py
rm -f /usr/local/bin/pve-hw-apply.py
rm -f /usr/local/bin/pve-hwinfo.sh
rm -f /usr/local/bin/pve-cpufreq-set.sh
rm -f /usr/local/bin/pve-cpus-set.sh
rm -f /usr/local/bin/pve-cpufreq-api.py
systemctl disable --now pve-cpufreq-api.service 2>/dev/null || true
rm -f /etc/systemd/system/pve-cpufreq-api.service
systemctl daemon-reload 2>/dev/null || true

systemctl restart pveproxy
echo "Done. Hard-refresh the browser (Ctrl+Shift+R)."
