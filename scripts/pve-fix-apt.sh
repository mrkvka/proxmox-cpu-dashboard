#!/bin/bash
# Fix common Proxmox apt-get update failures (exit code 100).
# Run on the Proxmox host as root: bash scripts/pve-fix-apt.sh
# Use --apply to comment enterprise repos and enable pve-no-subscription.
set -euo pipefail

APPLY=0
if [ "${1:-}" = "--apply" ]; then
    APPLY=1
fi

if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: run as root on the Proxmox host."
    exit 1
fi

if [ ! -f /usr/share/perl5/PVE/API2/Nodes.pm ]; then
    echo "ERROR: this does not look like a Proxmox VE host."
    exit 1
fi

detect_suite() {
    local suite=""
    if command -v pveversion &>/dev/null; then
        suite=$(pveversion -v 2>/dev/null | awk -F'[()]' '/running kernel/ {print $2; exit}')
    fi
    if [ -z "$suite" ] && [ -f /etc/os-release ]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        suite="${VERSION_CODENAME:-}"
    fi
    if [ -z "$suite" ]; then
        suite="bookworm"
        echo "WARNING: could not detect Debian suite; defaulting to $suite" >&2
    fi
    echo "$suite"
}

SUITE=$(detect_suite)
echo "== Proxmox apt diagnostics (suite: $SUITE) =="
echo ""

echo "-- Repository files --"
for f in /etc/apt/sources.list /etc/apt/sources.list.d/*.list; do
    [ -f "$f" ] || continue
    echo ">>> $f"
    grep -E '^(#)?deb ' "$f" 2>/dev/null || echo "    (no deb lines)"
    echo ""
done

echo "-- Last apt update errors (if any) --"
if [ -f /var/log/apt/term.log ]; then
    tail -n 30 /var/log/apt/term.log 2>/dev/null || true
else
    echo "(no /var/log/apt/term.log)"
fi
echo ""

echo "-- Trial: apt-get update --"
set +e
UPDATE_OUT=$(apt-get update 2>&1)
UPDATE_RC=$?
set -e
if [ "$UPDATE_RC" -eq 0 ]; then
    echo "OK: apt-get update succeeded."
    exit 0
fi

echo "FAILED: apt-get update exited with $UPDATE_RC"
echo "$UPDATE_OUT" | tail -n 40
echo ""

if echo "$UPDATE_OUT" | grep -qiE '401|403|enterprise\.proxmox'; then
    echo "LIKELY CAUSE: pve-enterprise (or ceph enterprise) without a subscription."
    echo "FIX: run this script with --apply, then apt-get update again."
fi
if echo "$UPDATE_OUT" | grep -qi 'NO_PUBKEY'; then
    echo "LIKELY CAUSE: missing GPG key. See README troubleshooting (GPG keys)."
fi
if echo "$UPDATE_OUT" | grep -qiE '404|not found|does not have a Release'; then
    echo "LIKELY CAUSE: wrong Debian suite in a .list file (expected: $SUITE)."
fi

if [ "$APPLY" -eq 0 ]; then
    echo ""
    echo "Dry-run only. To apply repo fixes: bash $0 --apply"
    exit "$UPDATE_RC"
fi

echo ""
echo "== Applying repository fixes =="
TS=$(date +%Y%m%d_%H%M%S)

fix_list_file() {
    local file="$1"
    [ -f "$file" ] || return 0
    cp -a "$file" "${file}.bak_${TS}"
    sed -i -E 's/^deb /# deb /' "$file"
    echo "Commented active deb lines in $file (backup: ${file}.bak_${TS})"
}

fix_list_file /etc/apt/sources.list.d/pve-enterprise.list
fix_list_file /etc/apt/sources.list.d/ceph.list

NO_SUB=/etc/apt/sources.list.d/pve-no-subscription.list
if [ -f "$NO_SUB" ]; then
    cp -a "$NO_SUB" "${NO_SUB}.bak_${TS}"
fi
cat > "$NO_SUB" <<EOF
# Proxmox VE no-subscription repository (added by pve-fix-apt.sh)
deb http://download.proxmox.com/debian/pve $SUITE pve-no-subscription
EOF
echo "Wrote $NO_SUB"

# Remove duplicate install-time repo if it conflicts
if [ -f /etc/apt/sources.list.d/pve-install-repo.list ]; then
    if ! grep -q 'pve-no-subscription' /etc/apt/sources.list.d/pve-install-repo.list 2>/dev/null; then
        fix_list_file /etc/apt/sources.list.d/pve-install-repo.list
    fi
fi

echo ""
echo "-- apt-get update after fix --"
apt-get update
echo ""
echo "Done. You can run upgrades from the UI or: apt full-upgrade"
