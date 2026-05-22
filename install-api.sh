#!/bin/bash
# Proxmox Node Hardware API — API only (no web UI)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"
SHARE_DIR="/usr/share/pve-node-hw-api"
FROM_DEB=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-deb) FROM_DEB=1; shift ;;
        --help|-h)
            echo "Usage: $0 [--from-deb]"
            echo "Installs /nodes/{node}/hw* API. For UI: install-ui.sh"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

HW_VER="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"

echo "=========================================="
echo " proxmox-node-hw-api v${HW_VER}"
echo "=========================================="

bash "$SCRIPT_DIR/scripts/pve-version-check.sh"

if ! command -v sensors &>/dev/null; then
    echo "[*] Installing lm-sensors..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y lm-sensors
fi

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "[*] Backup Nodes.pm (bak_${TIMESTAMP})..."
cp /usr/share/perl5/PVE/API2/Nodes.pm "/usr/share/perl5/PVE/API2/Nodes.pm.bak_${TIMESTAMP}"

echo "[*] Installing to ${SHARE_DIR}..."
install -d "$SHARE_DIR"
install -m 644 "$SCRIPT_DIR/VERSION" "$SHARE_DIR/VERSION"
install -m 755 "$SRC/pve-hw-collect.py" "$SHARE_DIR/pve-hw-collect.py"
install -m 755 "$SRC/pve-hw-apply.py" "$SHARE_DIR/pve-hw-apply.py"
install -m 755 "$SRC/pve-cpufreq-set.sh" "$SHARE_DIR/pve-cpufreq-set.sh"
install -m 755 "$SRC/pve-cpus-set.sh" "$SHARE_DIR/pve-cpus-set.sh"
install -m 755 "$SRC/patch-nodes.sh" "$SHARE_DIR/patch-nodes.sh"
install -d "$SHARE_DIR/perl/PVE/API2/Nodes"
install -m 644 "$SRC/perl/PVE/API2/Nodes/Hardware.pm" "$SHARE_DIR/perl/PVE/API2/Nodes/Hardware.pm"
install -d "$SHARE_DIR/docs"
install -m 644 "$SCRIPT_DIR/docs/"*.md "$SHARE_DIR/docs/" 2>/dev/null || true
install -m 755 "$SCRIPT_DIR/install-api.sh" "$SHARE_DIR/install-api.sh"
install -m 755 "$SCRIPT_DIR/uninstall-api.sh" "$SHARE_DIR/uninstall-api.sh"

install -m 755 "$SHARE_DIR/pve-hw-collect.py" /usr/local/bin/pve-hw-collect.py
install -m 755 "$SHARE_DIR/pve-hw-apply.py" /usr/local/bin/pve-hw-apply.py
install -m 755 "$SHARE_DIR/pve-cpufreq-set.sh" /usr/local/bin/pve-cpufreq-set.sh
install -m 755 "$SHARE_DIR/pve-cpus-set.sh" /usr/local/bin/pve-cpus-set.sh
install -d /usr/share/perl5/PVE/API2/Nodes
install -m 644 "$SHARE_DIR/perl/PVE/API2/Nodes/Hardware.pm" /usr/share/perl5/PVE/API2/Nodes/Hardware.pm

systemctl disable --now pve-cpufreq-api.service 2>/dev/null || true
rm -f /etc/systemd/system/pve-cpufreq-api.service /usr/local/bin/pve-cpufreq-api.py /usr/local/bin/pve-hwinfo.sh
systemctl daemon-reload 2>/dev/null || true

mkdir -p /var/cache/pve-hw-dashboard
chmod 755 /var/cache/pve-hw-dashboard

echo "[*] Testing collector..."
/usr/local/bin/pve-hw-collect.py --compact | python3 -c "import sys,json; d=json.load(sys.stdin); print('    OK', d['meta']['version'])"

echo "[*] Patching Nodes.pm..."
bash "$SHARE_DIR/patch-nodes.sh"

echo "[*] Restarting pvedaemon + pveproxy..."
systemctl restart pvedaemon pveproxy

bash "$SCRIPT_DIR/scripts/verify-patch.sh"

echo ""
echo " API installed. Test: pvesh get /nodes/\$(hostname -s)/hw"
echo " Optional UI: bash install-ui.sh"
echo " Docs: ${SHARE_DIR}/docs/API.md"
echo ""
