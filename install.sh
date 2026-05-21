#!/bin/bash
# Proxmox CPU Dashboard v2 — native PVE API (no :8087 sidecar)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"

echo "=========================================="
echo " Proxmox CPU Dashboard v2 — Installer"
echo "=========================================="

if [ ! -f /usr/share/perl5/PVE/API2/Nodes.pm ]; then
    echo "ERROR: Run this on a Proxmox VE host."
    exit 1
fi

if ! command -v sensors &>/dev/null; then
    echo "[*] Installing lm-sensors..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y lm-sensors
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "[*] Backups (bak_${TIMESTAMP})..."
cp /usr/share/perl5/PVE/API2/Nodes.pm "/usr/share/perl5/PVE/API2/Nodes.pm.bak_${TIMESTAMP}"
cp /usr/share/pve-manager/index.html.tpl "/usr/share/pve-manager/index.html.tpl.bak_${TIMESTAMP}"
[ -f /usr/share/pve-manager/js/pve_node_summary.js ] && \
    cp /usr/share/pve-manager/js/pve_node_summary.js "/usr/share/pve-manager/js/pve_node_summary.js.bak_${TIMESTAMP}"

echo "[*] Installing host tools..."
install -m 755 "$SRC/pve-hw-collect.py" /usr/local/bin/pve-hw-collect.py
install -m 755 "$SRC/pve-hw-apply.py" /usr/local/bin/pve-hw-apply.py
install -m 755 "$SRC/pve-hwinfo.sh" /usr/local/bin/pve-hwinfo.sh
install -m 755 "$SRC/pve-cpufreq-set.sh" /usr/local/bin/pve-cpufreq-set.sh
install -m 755 "$SRC/pve-cpus-set.sh" /usr/local/bin/pve-cpus-set.sh

if systemctl is-enabled pve-cpufreq-api.service &>/dev/null; then
    echo "[*] Disabling legacy pve-cpufreq-api (:8087)..."
    systemctl disable --now pve-cpufreq-api.service || true
fi
rm -f /etc/systemd/system/pve-cpufreq-api.service /usr/local/bin/pve-cpufreq-api.py
systemctl daemon-reload 2>/dev/null || true

echo "[*] Testing collector..."
/usr/local/bin/pve-hw-collect.py --compact | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['meta']['version']; print('    OK', d['meta']['version'], 'cpus', d['cpu']['online'], '/', d['cpu']['total'])"

echo "[*] Patching Nodes.pm (native API)..."
bash "$SRC/patch-nodes.sh"

echo "[*] Installing Summary UI..."
cp "$SRC/pve_node_summary.js" /usr/share/pve-manager/js/pve_node_summary.js
INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
if ! grep -q 'pve_node_summary.js' "$INDEX_TPL"; then
    sed -i '/pvemanagerlib.js/a\    <script type="text\/javascript" src="\/pve2\/js\/pve_node_summary.js?ver=2.3.2"><\/script>' "$INDEX_TPL"
fi

echo "[*] Restarting pvedaemon + pveproxy (required for new API routes)..."
systemctl restart pvedaemon pveproxy

echo ""
echo "=========================================="
echo " Installation complete (native API v2)"
echo "=========================================="
echo "  UI: Node -> Summary (Ctrl+Shift+R)"
echo "  API: https://$(hostname -f):8006/api2/json/nodes/$(hostname -s)/hw"
echo ""
