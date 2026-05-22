#!/bin/bash
# Proxmox CPU Dashboard v2 — native PVE API (no :8087 sidecar)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"
HW_VER="2.4.2"

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

echo "[*] Installing UI (Hardware tab)..."
cp "$SRC/pve_node_summary.js" /usr/share/pve-manager/js/pve_node_summary.js
cp "$SRC/pve_node_hardware.js" /usr/share/pve-manager/js/pve_node_hardware.js

INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
link_hw_js() {
    local js="$1"
    local tag="    <script type=\"text/javascript\" src=\"/pve2/js/${js}?ver=${HW_VER}\"></script>"
    if grep -q "/pve2/js/${js}" "$INDEX_TPL"; then
        sed -i "s|/pve2/js/${js}?ver=[^\"']*|/pve2/js/${js}?ver=${HW_VER}|g" "$INDEX_TPL"
        echo "    Updated $js in index.html.tpl"
    else
        sed -i "\|pve2/js/pvemanagerlib.js|a\\${tag}" "$INDEX_TPL"
        echo "    Linked $js in index.html.tpl"
    fi
}
link_hw_js pve_node_summary.js
link_hw_js pve_node_hardware.js
for js in pve_node_summary.js pve_node_hardware.js; do
    grep -q "/pve2/js/${js}" "$INDEX_TPL" || { echo "ERROR: ${js} not in index.html.tpl"; exit 1; }
done

echo "[*] Restarting pvedaemon + pveproxy (required for new API routes)..."
systemctl restart pvedaemon pveproxy

echo ""
echo "=========================================="
echo " Installation complete (native API v2)"
echo "=========================================="
echo "  UI: Node -> Hardware tab (2nd, under Summary)"
echo "  Hard refresh: Ctrl+Shift+R"
echo ""
