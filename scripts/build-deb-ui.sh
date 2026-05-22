#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(bash "$ROOT/scripts/read-version.sh")"
PKG="proxmox-node-hw-ui"
STAGE="$ROOT/dist/${PKG}_${VERSION}_all"
DEB="$ROOT/dist/${PKG}_${VERSION}_all.deb"

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$STAGE/usr/share/pve-node-hw-ui"

bash "$ROOT/scripts/gen-build-info.sh" "$ROOT/src/pve_hw_build_info.js"
install -m 644 "$ROOT/VERSION" "$STAGE/usr/share/pve-node-hw-ui/VERSION"
install -d "$STAGE/usr/share/pve-node-hw-ui/ui"
install -m 644 "$ROOT/src/ui/pve_hw_core.js" "$STAGE/usr/share/pve-node-hw-ui/ui/"
install -m 644 "$ROOT/src/ui/pve_hw_tab.js" "$STAGE/usr/share/pve-node-hw-ui/ui/"
install -m 644 "$ROOT/src/ui/pve_hw_plugin.js" "$STAGE/usr/share/pve-node-hw-ui/ui/"
install -m 644 "$ROOT/src/pve_hw_build_info.js" "$STAGE/usr/share/pve-node-hw-ui/"
install -m 755 "$ROOT/install-ui.sh" "$STAGE/usr/share/pve-node-hw-ui/install-ui.sh"
install -m 755 "$ROOT/uninstall-ui.sh" "$STAGE/usr/share/pve-node-hw-ui/uninstall-ui.sh"

cat > "$STAGE/DEBIAN/control" << EOF
Package: proxmox-node-hw-ui
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: all
Depends: pve-manager (>= 8.0), proxmox-node-hw-api (= ${VERSION})
Maintainer: Proxmox Node Hardware API <https://github.com/mrkvka/proxmox-cpu-dashboard>
Description: Proxmox VE Hardware tab (web UI)
 Minimal ExtJS plugin (core/tab/plugin) for Node → Hardware tab. Requires proxmox-node-hw-api.
EOF

cat > "$STAGE/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && [ -x /usr/share/pve-node-hw-ui/install-ui.sh ]; then
  DEBIAN_FRONTEND=noninteractive /usr/share/pve-node-hw-ui/install-ui.sh --from-deb
fi
EOF
chmod 755 "$STAGE/DEBIAN/postinst"
echo '#!/bin/sh' > "$STAGE/DEBIAN/prerm" && chmod 755 "$STAGE/DEBIAN/prerm"

mkdir -p "$ROOT/dist"
dpkg-deb --build "$STAGE" "$DEB"
echo "Built $DEB"
