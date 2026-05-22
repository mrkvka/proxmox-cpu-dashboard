#!/bin/bash
# Proxmox Node Hardware API — install on Proxmox VE 9.x
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"
SHARE_DIR="/usr/share/pve-node-hw-api"
INSTALL_UI=1
FROM_DEB=0

usage() {
    cat <<EOF
Usage: $0 [OPTIONS]

  --api-only     Install API + collector only (no web UI scripts)
  --from-deb     Called from Debian postinst (same as default)
  --help         Show this help

After 'apt upgrade pve-manager', re-run this script.
Docs: $SHARE_DIR/docs/API.md or https://github.com/mrkvka/proxmox-cpu-dashboard
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-only) INSTALL_UI=0; shift ;;
        --from-deb) FROM_DEB=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if [[ -f "$SCRIPT_DIR/VERSION" ]]; then
    HW_VER="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"
else
    HW_VER="0.0.0"
fi

echo "=========================================="
echo " Proxmox Node Hardware API v${HW_VER}"
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
if [[ "$INSTALL_UI" -eq 1 ]]; then
    cp /usr/share/pve-manager/index.html.tpl "/usr/share/pve-manager/index.html.tpl.bak_${TIMESTAMP}"
fi

echo "[*] Installing package files to ${SHARE_DIR}..."
install -d "$SHARE_DIR"
install -m 644 "$SCRIPT_DIR/VERSION" "$SHARE_DIR/VERSION"
install -m 755 "$SRC/pve-hw-collect.py" "$SHARE_DIR/pve-hw-collect.py"
install -m 755 "$SRC/pve-hw-apply.py" "$SHARE_DIR/pve-hw-apply.py"
install -m 755 "$SRC/pve-cpufreq-set.sh" "$SHARE_DIR/pve-cpufreq-set.sh"
install -m 755 "$SRC/pve-cpus-set.sh" "$SHARE_DIR/pve-cpus-set.sh"
install -m 755 "$SRC/patch-nodes.sh" "$SHARE_DIR/patch-nodes.sh"
install -d "$SHARE_DIR/perl/PVE/API2/Nodes"
install -m 644 "$SRC/perl/PVE/API2/Nodes/Hardware.pm" "$SHARE_DIR/perl/PVE/API2/Nodes/Hardware.pm"
if [[ -d "$SCRIPT_DIR/docs" ]]; then
    install -d "$SHARE_DIR/docs"
    install -m 644 "$SCRIPT_DIR/docs/"*.md "$SHARE_DIR/docs/" 2>/dev/null || true
fi

install -m 755 "$SHARE_DIR/pve-hw-collect.py" /usr/local/bin/pve-hw-collect.py
install -m 755 "$SHARE_DIR/pve-hw-apply.py" /usr/local/bin/pve-hw-apply.py
install -m 755 "$SHARE_DIR/pve-cpufreq-set.sh" /usr/local/bin/pve-cpufreq-set.sh
install -m 755 "$SHARE_DIR/pve-cpus-set.sh" /usr/local/bin/pve-cpus-set.sh
install -d /usr/share/perl5/PVE/API2/Nodes
install -m 644 "$SHARE_DIR/perl/PVE/API2/Nodes/Hardware.pm" /usr/share/perl5/PVE/API2/Nodes/Hardware.pm

if systemctl is-enabled pve-cpufreq-api.service &>/dev/null; then
    echo "[*] Disabling legacy pve-cpufreq-api (:8087)..."
    systemctl disable --now pve-cpufreq-api.service || true
fi
rm -f /etc/systemd/system/pve-cpufreq-api.service /usr/local/bin/pve-cpufreq-api.py /usr/local/bin/pve-hwinfo.sh
systemctl daemon-reload 2>/dev/null || true

mkdir -p /var/cache/pve-hw-dashboard
chmod 755 /var/cache/pve-hw-dashboard

echo "[*] Testing collector..."
/usr/local/bin/pve-hw-collect.py --compact | python3 -c "import sys,json; d=json.load(sys.stdin); assert d['meta']['version']; print('    OK', d['meta']['version'], 'cpus', d['cpu']['online'], '/', d['cpu']['total'])"

echo "[*] Patching Nodes.pm..."
bash "$SHARE_DIR/patch-nodes.sh"

if [[ "$INSTALL_UI" -eq 1 ]]; then
    echo "[*] Installing UI (Hardware tab)..."
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
else
    echo "[*] Skipping UI (--api-only)"
fi

echo "[*] Restarting pvedaemon + pveproxy..."
systemctl restart pvedaemon pveproxy

echo "[*] Verifying..."
bash "$SCRIPT_DIR/scripts/verify-patch.sh"

echo ""
if [[ "$INSTALL_UI" -eq 1 ]]; then
    echo " Done v${HW_VER}. Node → Hardware tab. Ctrl+Shift+R in browser."
else
    echo " Done v${HW_VER} (API only). Test: pvesh get /nodes/\$(hostname -s)/hw"
fi
echo " Docs: ${SHARE_DIR}/docs/API.md"
echo " After pve-manager upgrade: bash install.sh"
echo ""
