#!/bin/bash
# Proxmox CPU Dashboard v3.1.0 — native PVE API (no :8087 sidecar)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"
HW_VER="3.1.0"

echo "=========================================="
echo " Proxmox CPU Dashboard v${HW_VER} — Installer"
echo "=========================================="

bash "$SCRIPT_DIR/scripts/pve-version-check.sh"

if ! command -v sensors &>/dev/null; then
    echo "[*] Installing lm-sensors..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y lm-sensors
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "[*] Backups (bak_${TIMESTAMP})..."
cp /usr/share/perl5/PVE/API2/Nodes.pm "/usr/share/perl5/PVE/API2/Nodes.pm.bak_${TIMESTAMP}"
cp /usr/share/pve-manager/index.html.tpl "/usr/share/pve-manager/index.html.tpl.bak_${TIMESTAMP}"

echo "[*] Installing host tools..."
install -m 755 "$SRC/pve-hw-collect.py" /usr/local/bin/pve-hw-collect.py
install -m 755 "$SRC/pve-hw-apply.py" /usr/local/bin/pve-hw-apply.py
install -m 755 "$SRC/pve-hwinfo.sh" /usr/local/bin/pve-hwinfo.sh
install -m 755 "$SRC/pve-cpufreq-set.sh" /usr/local/bin/pve-cpufreq-set.sh
install -m 755 "$SRC/pve-cpus-set.sh" /usr/local/bin/pve-cpus-set.sh

install -d /usr/share/perl5/PVE/API2/Nodes
install -m 644 "$SRC/perl/PVE/API2/Nodes/Hardware.pm" /usr/share/perl5/PVE/API2/Nodes/Hardware.pm

if systemctl is-enabled pve-cpufreq-api.service &>/dev/null; then
    echo "[*] Disabling legacy pve-cpufreq-api (:8087)..."
    systemctl disable --now pve-cpufreq-api.service || true
fi
rm -f /etc/systemd/system/pve-cpufreq-api.service /usr/local/bin/pve-cpufreq-api.py
systemctl daemon-reload 2>/dev/null || true

mkdir -p /var/cache/pve-hw-dashboard
chmod 755 /var/cache/pve-hw-dashboard

echo "[*] Testing collector..."
/usr/local/bin/pve-hw-collect.py --compact | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['meta']['version']; print('    OK', d['meta']['version'], 'cpus', d['cpu']['online'], '/', d['cpu']['total'])"

echo "[*] Patching Nodes.pm (hardware API module)..."
bash "$SRC/patch-nodes.sh"

echo "[*] Installing UI..."
cp "$SRC/pve_node_summary.js" /usr/share/pve-manager/js/pve_node_summary.js
cp "$SRC/pve_node_hardware.js" /usr/share/pve-manager/js/pve_node_hardware.js

INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
sed -i '\|/pve2/js/pve_node_summary.js|d' "$INDEX_TPL"
sed -i '\|/pve2/js/pve_node_hardware.js|d' "$INDEX_TPL"
SUM_TAG="    <script type=\"text/javascript\" src=\"/pve2/js/pve_node_summary.js?ver=${HW_VER}\"></script>"
HW_TAG="    <script type=\"text/javascript\" src=\"/pve2/js/pve_node_hardware.js?ver=${HW_VER}\"></script>"
sed -i "\|pve2/js/pvemanagerlib.js|a\\${SUM_TAG}" "$INDEX_TPL"
sed -i "\|pve2/js/pve_node_summary.js|a\\${HW_TAG}" "$INDEX_TPL"
grep -q pve_node_summary.js "$INDEX_TPL" && grep -q pve_node_hardware.js "$INDEX_TPL"
echo "    Scripts linked (summary -> hardware)"

echo "[*] Restarting pvedaemon + pveproxy..."
systemctl restart pvedaemon pveproxy

echo "[*] Verifying installation..."
bash "$SCRIPT_DIR/scripts/verify-patch.sh"

echo ""
echo " Done v${HW_VER}. Node menu: Summary, Hardware (2nd), ..."
echo " After 'apt upgrade pve-manager' re-run: bash install.sh"
echo " Ctrl+Shift+R in browser"
echo ""
