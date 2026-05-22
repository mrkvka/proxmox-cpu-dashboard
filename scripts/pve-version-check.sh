#!/bin/bash
# Verify Proxmox VE version and Nodes.pm patch anchor before install.
set -euo pipefail

MIN_MAJOR=9
MIN_MINOR=0
NODES_PM="/usr/share/perl5/PVE/API2/Nodes.pm"

if [ ! -f "$NODES_PM" ]; then
    echo "ERROR: Not a Proxmox VE host ($NODES_PM missing)."
    exit 1
fi

if ! command -v pveversion >/dev/null 2>&1; then
    echo "ERROR: pveversion not found."
    exit 1
fi

RAW=$(pveversion 2>/dev/null | head -1)
# Examples: pve-manager/9.2.2/... or proxmox-ve: 9.2.0
VER=$(echo "$RAW" | sed -nE 's/.*pve-manager\/([0-9]+)\.([0-9]+).*/\1.\2/p')
if [ -z "$VER" ]; then
    VER=$(echo "$RAW" | sed -nE 's/.*proxmox-ve: ([0-9]+)\.([0-9]+).*/\1.\2/p')
fi
if [ -z "$VER" ]; then
    echo "WARNING: Could not parse PVE version from: $RAW"
    echo "         Continuing if Nodes.pm anchor looks valid."
else
    MAJOR=${VER%%.*}
    MINOR=${VER#*.}
    if [ "$MAJOR" -lt "$MIN_MAJOR" ] || { [ "$MAJOR" -eq "$MIN_MAJOR" ] && [ "$MINOR" -lt "$MIN_MINOR" ]; }; then
        echo "ERROR: Proxmox VE $VER is not supported (need >= ${MIN_MAJOR}.${MIN_MINOR})."
        exit 1
    fi
    echo "OK: Proxmox VE $VER"
fi

if grep -qF 'PVE-HW-DASHBOARD: begin' "$NODES_PM"; then
    echo "OK: Nodes.pm already patched (reinstall safe)"
elif grep -qF 'package PVE::API2::Nodes;' "$NODES_PM" && grep -qE 'thermalstate.*sensors -jA' "$NODES_PM"; then
    echo "OK: Nodes.pm anchor found (stock thermalstate)"
elif grep -qF 'PVE::API2::Nodes::Hardware' "$NODES_PM"; then
    echo "OK: Nodes.pm has hardware module reference"
else
    echo "ERROR: Nodes.pm does not match expected Proxmox 9.x layout."
    echo "       Re-run after pve-manager upgrade or open a GitHub issue with: pveversion -v"
    exit 1
fi

exit 0
