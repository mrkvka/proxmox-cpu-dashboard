#!/bin/bash
# Quick health check for Proxmox + Proxmox CPU Dashboard.
# Run on the host as root: bash scripts/pve-health-check.sh
set -uo pipefail

WARN=0
FAIL=0

ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; WARN=$((WARN + 1)); }
fail() { echo "[FAIL] $*"; FAIL=$((FAIL + 1)); }

if [ "$(id -u)" -ne 0 ]; then
    echo "Run as root on the Proxmox host."
    exit 1
fi

echo "======== Proxmox health check ========"
echo ""

if command -v pveversion &>/dev/null; then
    ok "PVE: $(pveversion)"
else
    warn "pveversion not found"
fi

if command -v sensors &>/dev/null; then
    ok "lm-sensors installed"
else
    warn "lm-sensors missing (needed for temperatures). Install: apt-get install -y lm-sensors"
fi

if [ -d /sys/devices/system/cpu/cpu0/cpufreq ]; then
    ok "cpufreq sysfs present"
    if [ -r /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
        gov=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo "?")
        ok "Governor: $gov"
    else
        warn "Cannot read scaling_governor (permissions?)"
    fi
else
    warn "No cpufreq scaling (VM host passthrough or BIOS settings?)"
fi

echo ""
echo "-- apt --"
set +e
apt-get update -qq 2>/dev/null
APT_RC=$?
set -e
if [ "$APT_RC" -eq 0 ]; then
    ok "apt-get update"
else
    fail "apt-get update failed (exit $APT_RC). Run: bash scripts/pve-fix-apt.sh"
fi

echo ""
echo "-- CPU Dashboard install --"
for f in /usr/local/bin/pve-hwinfo.sh /usr/local/bin/pve-cpufreq-api.py; do
    if [ -x "$f" ]; then ok "Found $f"; else warn "Missing $f (run install.sh)"; fi
done

if systemctl is-active --quiet pve-cpufreq-api.service 2>/dev/null; then
    ok "pve-cpufreq-api.service active"
    if curl -sf --max-time 2 http://127.0.0.1:8087/health >/dev/null 2>&1; then
        ok "API http://127.0.0.1:8087/health"
    else
        warn "API not responding on :8087"
    fi
else
    warn "pve-cpufreq-api.service not running"
fi

if grep -q 'pve-hwinfo.sh' /usr/share/perl5/PVE/API2/Nodes.pm 2>/dev/null; then
    ok "Nodes.pm patched (thermalstate)"
else
    warn "Nodes.pm not patched — Summary thermals may be empty"
fi

if [ -f /usr/share/pve-manager/js/pve_node_summary.js ]; then
    ok "pve_node_summary.js installed"
else
    warn "JS override missing"
fi

if [ -x /usr/local/bin/pve-hwinfo.sh ]; then
    if /usr/local/bin/pve-hwinfo.sh 2>/dev/null | grep -q '"cpufreq"'; then
        ok "pve-hwinfo.sh returns cpufreq JSON"
    else
        warn "pve-hwinfo.sh output looks wrong"
    fi
fi

echo ""
echo "-- Services --"
for svc in pveproxy pvedaemon pvestatd; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        ok "$svc"
    else
        fail "$svc not active"
    fi
done

echo ""
echo "Summary: $FAIL failure(s), $WARN warning(s)"
if [ "$FAIL" -gt 0 ]; then
    exit 2
fi
if [ "$WARN" -gt 0 ]; then
    exit 1
fi
exit 0
