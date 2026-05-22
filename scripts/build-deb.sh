#!/bin/bash
# Build binary .deb for Proxmox VE host (requires dpkg-deb).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(bash "$ROOT/scripts/read-version.sh")"
PKG="proxmox-node-hw-api"
STAGE="$ROOT/dist/${PKG}_${VERSION}_all"
DEB="$ROOT/dist/${PKG}_${VERSION}_all.deb"

rm -rf "$STAGE"
mkdir -p "$STAGE/DEBIAN"
mkdir -p "$STAGE/usr/share/pve-node-hw-api"
mkdir -p "$STAGE/usr/share/perl5/PVE/API2/Nodes"

cp -a "$ROOT/src" "$ROOT/scripts" "$ROOT/docs" "$ROOT/LICENSE" \
    "$ROOT/install.sh" "$ROOT/uninstall.sh" "$ROOT/VERSION" \
    "$ROOT/README.md" "$ROOT/SECURITY.md" "$ROOT/UPGRADE.md" "$ROOT/CONTRIBUTING.md" \
    "$STAGE/usr/share/pve-node-hw-api/"

cp "$ROOT/src/perl/PVE/API2/Nodes/Hardware.pm" "$STAGE/usr/share/perl5/PVE/API2/Nodes/Hardware.pm"

cat > "$STAGE/DEBIAN/control" << EOF
Package: proxmox-node-hw-api
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: all
Depends: pve-manager (>= 8.0), lm-sensors, python3:any
Recommends: smartmontools
Maintainer: Proxmox Node Hardware API <https://github.com/mrkvka/proxmox-cpu-dashboard>
Description: Native Proxmox VE node hardware API and optional UI
 Extends PVE API with /nodes/{node}/hw, live inventory, and CPU control.
 No separate HTTP port. Optional Hardware tab in the web UI.
EOF

cat > "$STAGE/DEBIAN/postinst" << 'EOF'
#!/bin/sh
set -e
if [ "$1" = configure ]; then
  if [ -x /usr/share/pve-node-hw-api/install.sh ]; then
    DEBIAN_FRONTEND=noninteractive /usr/share/pve-node-hw-api/install.sh --from-deb
  fi
fi
EOF

cat > "$STAGE/DEBIAN/prerm" << 'EOF'
#!/bin/sh
set -e
EOF

chmod 755 "$STAGE/DEBIAN/postinst" "$STAGE/DEBIAN/prerm"
mkdir -p "$ROOT/dist"
dpkg-deb --build "$STAGE" "$DEB"
echo "Built $DEB"
