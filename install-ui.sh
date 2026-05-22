#!/bin/bash
# Proxmox Node Hardware UI — Hardware tab (requires proxmox-node-hw-api)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"
SHARE_UI="/usr/share/pve-node-hw-ui"
API_SHARE="/usr/share/pve-node-hw-api"

usage() {
    echo "Usage: $0 [--from-deb]"
    echo "Requires: proxmox-node-hw-api (bash install-api.sh)"
}

FROM_DEB=0
while [[ $# -gt 0 ]]; do
    case "$1" in
        --from-deb) FROM_DEB=1; shift ;;
        --help|-h) usage; exit 0 ;;
        *) echo "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if ! grep -qF 'PVE-HW-DASHBOARD: begin' /usr/share/perl5/PVE/API2/Nodes.pm 2>/dev/null; then
    echo "ERROR: API not installed. Run: bash install-api.sh"
    exit 1
fi

HW_VER="$(tr -d '[:space:]' < "$SCRIPT_DIR/VERSION")"
if [[ -f "$API_SHARE/VERSION" ]]; then
    API_VER="$(tr -d '[:space:]' < "$API_SHARE/VERSION")"
    if [[ "$API_VER" != "$HW_VER" ]]; then
        echo "WARNING: UI version ${HW_VER} != API version ${API_VER}"
    fi
fi


bash "$SCRIPT_DIR/scripts/gen-build-info.sh"
BUILD_JS="$SRC/pve_hw_build_info.js"
echo "=========================================="
echo " proxmox-node-hw-ui v${HW_VER}"
echo "=========================================="

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "[*] Backup index.html.tpl (bak_${TIMESTAMP})..."
cp /usr/share/pve-manager/index.html.tpl "/usr/share/pve-manager/index.html.tpl.bak_${TIMESTAMP}"

install -d "$SHARE_UI"
install -m 644 "$SCRIPT_DIR/VERSION" "$SHARE_UI/VERSION"
install -m 644 "$SRC/pve_node_summary.js" "$SHARE_UI/pve_node_summary.js"
install -m 644 "$SRC/pve_node_hardware.js" "$SHARE_UI/pve_node_hardware.js"
install -m 644 "$BUILD_JS" "$SHARE_UI/pve_hw_build_info.js"
install -m 755 "$SCRIPT_DIR/install-ui.sh" "$SHARE_UI/install-ui.sh"
install -m 755 "$SCRIPT_DIR/uninstall-ui.sh" "$SHARE_UI/uninstall-ui.sh"

cp "$SRC/pve_node_summary.js" /usr/share/pve-manager/js/pve_node_summary.js
cp "$SRC/pve_node_hardware.js" /usr/share/pve-manager/js/pve_node_hardware.js
cp "$BUILD_JS" /usr/share/pve-manager/js/pve_hw_build_info.js

INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
sed -i '\|/pve2/js/pve_node_summary.js|d' "$INDEX_TPL"
sed -i '\|/pve2/js/pve_node_hardware.js|d' "$INDEX_TPL"
sed -i '\|/pve2/js/pve_hw_build_info.js|d' "$INDEX_TPL"
SUM_TAG="    <script type=\"text/javascript\" src=\"/pve2/js/pve_node_summary.js?ver=${HW_VER}\"></script>"
HW_TAG="    <script type=\"text/javascript\" src=\"/pve2/js/pve_node_hardware.js?ver=${HW_VER}\"></script>"
ABOUT_TAG="    <script type=\"text/javascript\" src=\"/pve2/js/pve_hw_build_info.js?ver=${HW_VER}\"></script>"
sed -i "\|pve2/js/pvemanagerlib.js|a\\${SUM_TAG}" "$INDEX_TPL"
sed -i "\|pve2/js/pve_node_summary.js|a\\${HW_TAG}" "$INDEX_TPL"
sed -i "\|pve2/js/pve_node_hardware.js|a\\${ABOUT_TAG}" "$INDEX_TPL"
grep -q pve_hw_build_info.js "$INDEX_TPL" && grep -q pve_node_summary.js "$INDEX_TPL" && grep -q pve_node_hardware.js "$INDEX_TPL"

echo "[*] Restarting pveproxy..."
systemctl restart pveproxy

bash "$SCRIPT_DIR/scripts/verify-ui.sh"

echo ""
echo " UI installed. Node → Hardware tab, then Ctrl+Shift+R"
echo ""
