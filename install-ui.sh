#!/bin/bash
# Proxmox Node Hardware UI — minimal ExtJS plugin (requires proxmox-node-hw-api)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UI_SRC="$SCRIPT_DIR/src/ui"
SHARE_UI="/usr/share/pve-node-hw-ui"
API_SHARE="/usr/share/pve-node-hw-api"
MGR_JS="/usr/share/pve-manager/js"
INDEX_TPL="/usr/share/pve-manager/index.html.tpl"

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

for f in pve_hw_core.js pve_hw_tab.js pve_hw_plugin.js; do
    if [[ ! -f "$UI_SRC/$f" ]]; then
        echo "ERROR: missing $UI_SRC/$f"
        exit 1
    fi
done

bash "$SCRIPT_DIR/scripts/gen-build-info.sh" "$SCRIPT_DIR/src/pve_hw_build_info.js"
BUILD_JS="$SCRIPT_DIR/src/pve_hw_build_info.js"

echo "=========================================="
echo " proxmox-node-hw-ui v${HW_VER}"
echo "=========================================="

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "[*] Backup index.html.tpl (bak_${TIMESTAMP})..."
cp "$INDEX_TPL" "${INDEX_TPL}.bak_${TIMESTAMP}"

install -d "$SHARE_UI" "$SHARE_UI/ui"
install -m 644 "$SCRIPT_DIR/VERSION" "$SHARE_UI/VERSION"
install -m 644 "$UI_SRC/pve_hw_core.js" "$SHARE_UI/ui/pve_hw_core.js"
install -m 644 "$UI_SRC/pve_hw_tab.js" "$SHARE_UI/ui/pve_hw_tab.js"
install -m 644 "$UI_SRC/pve_hw_plugin.js" "$SHARE_UI/ui/pve_hw_plugin.js"
install -m 644 "$BUILD_JS" "$SHARE_UI/pve_hw_build_info.js"
install -m 755 "$SCRIPT_DIR/install-ui.sh" "$SHARE_UI/install-ui.sh"
install -m 755 "$SCRIPT_DIR/uninstall-ui.sh" "$SHARE_UI/uninstall-ui.sh"

# Strip script tags (legacy + current), then deploy /pve2/js/ files
ALL_UI_SCRIPTS=(pve_node_summary.js pve_node_hardware.js pve_hw_core.js pve_hw_tab.js pve_hw_plugin.js pve_hw_build_info.js)
for f in "${ALL_UI_SCRIPTS[@]}"; do
    sed -i "\\|/pve2/js/${f}|d" "$INDEX_TPL"
    rm -f "$MGR_JS/$f"
done

install -m 644 "$UI_SRC/pve_hw_core.js" "$MGR_JS/pve_hw_core.js"
install -m 644 "$UI_SRC/pve_hw_tab.js" "$MGR_JS/pve_hw_tab.js"
install -m 644 "$UI_SRC/pve_hw_plugin.js" "$MGR_JS/pve_hw_plugin.js"
install -m 644 "$BUILD_JS" "$MGR_JS/pve_hw_build_info.js"

inject_after() {
    local anchor="$1"
    local file="$2"
    local tag="    <script type=\"text/javascript\" src=\"/pve2/js/${file}?ver=${HW_VER}\"></script>"
    if ! grep -qF "/pve2/js/${file}" "$INDEX_TPL"; then
        sed -i "\|${anchor}|a\${tag}" "$INDEX_TPL"
    fi
}

inject_after "pve2/js/pvemanagerlib.js" pve_hw_core.js
inject_after "pve2/js/pve_hw_core.js" pve_hw_tab.js
inject_after "pve2/js/pve_hw_tab.js" pve_hw_plugin.js
inject_after "pve2/js/pve_hw_plugin.js" pve_hw_build_info.js
grep -q pve_hw_core.js "$INDEX_TPL"
grep -q pve_hw_tab.js "$INDEX_TPL"
grep -q pve_hw_plugin.js "$INDEX_TPL"
grep -q pve_hw_build_info.js "$INDEX_TPL"

echo "[*] Restarting pveproxy..."
systemctl restart pveproxy

bash "$SCRIPT_DIR/scripts/verify-ui.sh"

echo ""
echo " UI installed. Node → Hardware tab, then Ctrl+Shift+R"
echo " Load order: core → tab → plugin → build_info (see docs/PLUGIN.md)"
echo ""
