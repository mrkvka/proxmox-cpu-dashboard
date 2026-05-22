#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(bash "$ROOT/scripts/read-version.sh")"
PKG="proxmox-node-hw-api"
STAGE="$ROOT/dist/${PKG}_${VERSION}_all"
DEB="$ROOT/dist/${PKG}_${VERSION}_all.deb"
DEST="$STAGE/usr/share/pve-node-hw-api"

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN" "$DEST" "$STAGE/usr/share/perl5/PVE/API2/Nodes"

cp -a "$ROOT/src" "$ROOT/scripts" "$ROOT/docs" "$DEST/"
rm -f "$DEST/src/pve_node_summary.js" "$DEST/src/pve_node_hardware.js"
cp "$ROOT/VERSION" "$ROOT/LICENSE" "$ROOT/README.md" "$ROOT/SECURITY.md" "$ROOT/UPGRADE.md" "$DEST/" 2>/dev/null || true
cp "$ROOT/install-api.sh" "$ROOT/uninstall-api.sh" "$DEST/"
chmod 755 "$DEST/install-api.sh" "$DEST/uninstall-api.sh"

cp "$ROOT/src/perl/PVE/API2/Nodes/Hardware.pm" "$STAGE/usr/share/perl5/PVE/API2/Nodes/Hardware.pm"

cat > "$STAGE/DEBIAN/control" << EOF
Package: proxmox-node-hw-api
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: all
Depends: pve-manager (>= 8.0), lm-sensors, python3:any
Recommends: smartmontools, proxmox-node-hw-ui
Maintainer: Proxmox Node Hardware API <https://github.com/mrkvka/proxmox-cpu-dashboard>
Description: Native Proxmox VE node hardware API
 CPU/hardware JSON API on PVE port 8006: /nodes/{node}/hw, hwlive, hwapply.
 No separate HTTP service. Install proxmox-node-hw-ui for the web tab.
EOF

cat > "$STAGE/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ] && [ -x /usr/share/pve-node-hw-api/install-api.sh ]; then
  DEBIAN_FRONTEND=noninteractive /usr/share/pve-node-hw-api/install-api.sh --from-deb
fi
EOF
chmod 755 "$STAGE/DEBIAN/postinst"
printf '#!/bin/sh\nset -e\n' > "$STAGE/DEBIAN/prerm" && chmod 755 "$STAGE/DEBIAN/prerm"

mkdir -p "$ROOT/dist"
dpkg-deb --build "$STAGE" "$DEB"
echo "Built $DEB"
