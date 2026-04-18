#!/bin/bash
# Proxmox CPU Dashboard - Installer
# Adds CPU frequency monitoring & control to Proxmox VE Summary page
# Tested on PVE 9.x with AMD/Intel CPUs
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$SCRIPT_DIR/src"

echo "=========================================="
echo " Proxmox CPU Dashboard - Installer"
echo "=========================================="

# Check if running on Proxmox
if [ ! -f /usr/share/perl5/PVE/API2/Nodes.pm ]; then
    echo "ERROR: This script must be run on a Proxmox VE host!"
    exit 1
fi

# Check if lm-sensors is installed
if ! command -v sensors &>/dev/null; then
    echo "[*] Installing lm-sensors..."
    apt-get install -y lm-sensors
fi

# Backup originals
echo "[*] Creating backups..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
cp /usr/share/perl5/PVE/API2/Nodes.pm "/usr/share/perl5/PVE/API2/Nodes.pm.bak_${TIMESTAMP}"
cp /usr/share/pve-manager/index.html.tpl "/usr/share/pve-manager/index.html.tpl.bak_${TIMESTAMP}"
if [ -f /usr/share/pve-manager/js/pve_node_summary.js ]; then
    cp /usr/share/pve-manager/js/pve_node_summary.js "/usr/share/pve-manager/js/pve_node_summary.js.bak_${TIMESTAMP}"
fi
echo "    Backups saved with suffix: bak_${TIMESTAMP}"

# Install scripts
echo "[*] Installing helper scripts..."
cp "$SRC/pve-hwinfo.sh" /usr/local/bin/pve-hwinfo.sh
cp "$SRC/pve-cpufreq-set.sh" /usr/local/bin/pve-cpufreq-set.sh
cp "$SRC/pve-cpus-set.sh" /usr/local/bin/pve-cpus-set.sh
cp "$SRC/pve-cpufreq-api.py" /usr/local/bin/pve-cpufreq-api.py
chmod +x /usr/local/bin/pve-hwinfo.sh /usr/local/bin/pve-cpufreq-set.sh /usr/local/bin/pve-cpus-set.sh /usr/local/bin/pve-cpufreq-api.py

# Install and start the API service
echo "[*] Installing pve-cpufreq-api.service..."
cp "$SRC/pve-cpufreq-api.service" /etc/systemd/system/pve-cpufreq-api.service
systemctl daemon-reload
systemctl enable --now pve-cpufreq-api.service
sleep 1
if systemctl is-active --quiet pve-cpufreq-api.service; then
    echo "    OK - pve-cpufreq-api running on :8087"
else
    echo "    WARNING: service failed to start. Run: journalctl -u pve-cpufreq-api -n 50"
fi

# Test hwinfo script
echo "[*] Testing pve-hwinfo.sh..."
OUTPUT=$(/usr/local/bin/pve-hwinfo.sh 2>&1)
if echo "$OUTPUT" | grep -q '"cpufreq"'; then
    echo "    OK - hwinfo script works"
else
    echo "    WARNING: hwinfo script may not be working correctly"
    echo "    Output: $OUTPUT"
fi

# Patch Nodes.pm - thermalstate
echo "[*] Patching Nodes.pm..."
NODES_PM="/usr/share/perl5/PVE/API2/Nodes.pm"

# Check if already patched
if grep -q 'pve-hwinfo.sh' "$NODES_PM"; then
    echo "    Already patched (thermalstate) - skipping"
else
    # Check if original thermalstate exists
    if grep -q 'sensors -jA' "$NODES_PM"; then
        sed -i 's|\$res->{thermalstate} = `sensors -jA`;|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|' "$NODES_PM"
        echo "    Patched thermalstate (replaced sensors -jA)"
    elif grep -q 'thermalstate' "$NODES_PM"; then
        sed -i 's|\$res->{thermalstate} = .*|\$res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;|' "$NODES_PM"
        echo "    Patched thermalstate (replaced existing)"
    else
        # Add thermalstate after pveversion line
        sed -i '/\$res->{pveversion}/a\    $res->{thermalstate} = `/usr/local/bin/pve-hwinfo.sh`;' "$NODES_PM"
        echo "    Added thermalstate line"
    fi
fi

# Add cpufreq POST endpoint
if grep -q 'cpufreq' "$NODES_PM"; then
    echo "    Already patched (cpufreq endpoint) - skipping"
else
    echo "[*] Adding cpufreq API endpoint..."
    bash "$SRC/patch-nodes.sh"
    echo "    cpufreq endpoint added"
fi

# Install JS override
echo "[*] Installing JS frontend..."
cp "$SRC/pve_node_summary.js" /usr/share/pve-manager/js/pve_node_summary.js

# Ensure JS is linked in index.html.tpl
INDEX_TPL="/usr/share/pve-manager/index.html.tpl"
if grep -q 'pve_node_summary.js' "$INDEX_TPL"; then
    echo "    JS already linked in index.html.tpl"
else
    sed -i '/pvemanagerlib.js/a\    <script type="text\/javascript" src="\/pve2\/js\/pve_node_summary.js?ver=[% version %]"><\/script>' "$INDEX_TPL"
    echo "    JS linked in index.html.tpl"
fi

# Restart pveproxy
echo "[*] Restarting pveproxy..."
systemctl restart pveproxy

echo ""
echo "=========================================="
echo " Installation complete!"
echo "=========================================="
echo ""
echo " Open Proxmox web UI and go to:"
echo "   Node -> Summary"
echo ""
echo " You should see:"
echo "   - Thermals (color-coded temperatures)"
echo "   - CPU Frequency (governor, frequencies, per-core)"
echo "   - Controls (governor dropdown, freq input, presets)"
echo "   - Fans (if available)"
echo ""
echo " Press Ctrl+Shift+R in browser to force reload."
echo ""
echo " API endpoints:"
echo "   GET  http://$(hostname -I | awk '{print $1}'):8087/health"
echo "   GET  http://$(hostname -I | awk '{print $1}'):8087/status"
echo "   POST http://$(hostname -I | awk '{print $1}'):8087/cpufreq"
echo ""
echo " Home Assistant: add this repo as a HACS Custom Repository,"
echo " or copy custom_components/proxmox_cpu_ctl/ to HA's /config/custom_components/"
echo ""
