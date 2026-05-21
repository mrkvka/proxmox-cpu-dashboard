#!/bin/bash
# Collect every CPU/thermal/power parameter exposed by sysfs, lm-sensors,
# pve-hwinfo, and the dashboard API. Writes JSON to stdout or AUDIT_OUT file.
set -euo pipefail

AUDIT_OUT="${1:-}"
STAMP=$(date -Iseconds)
HOST=$(hostname)

emit() {
    if [ -n "$AUDIT_OUT" ]; then
        cat > "$AUDIT_OUT"
        echo "Audit written to $AUDIT_OUT"
    else
        cat
    fi
}

python3 << PY | emit
import glob
import json
import os
import subprocess
import urllib.request

def read_text(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except Exception:
        return None

def read_int(path):
    value = read_text(path)
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None

def run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=20, check=False)
        return {
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as err:
        return {"cmd": cmd, "error": str(err)}

def fetch_json(url):
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            return json.loads(resp.read().decode())
    except Exception as err:
        return {"error": str(err), "url": url}

cpus = []
for online_path in sorted(glob.glob("/sys/devices/system/cpu/cpu[0-9]*/online")):
    cpu_dir = os.path.dirname(online_path)
    cpu_id = int(os.path.basename(cpu_dir).replace("cpu", ""))
    online = read_int(online_path)
    if online is None and cpu_id == 0:
        online = 1
    cpufreq = os.path.join(cpu_dir, "cpufreq")
    freq = {}
    if os.path.isdir(cpufreq):
        for name in sorted(os.listdir(cpufreq)):
            path = os.path.join(cpufreq, name)
            if os.path.isfile(path):
                text = read_text(path)
                if text is not None and text.isdigit():
                    freq[name] = int(text)
                else:
                    freq[name] = text
    topo = {}
    topo_dir = os.path.join(cpu_dir, "topology")
    if os.path.isdir(topo_dir):
        for name in sorted(os.listdir(topo_dir)):
            path = os.path.join(topo_dir, name)
            if os.path.isfile(path):
                topo[name] = read_text(path)
    cpus.append({"id": cpu_id, "online": online, "cpufreq": freq, "topology": topo})

powercap = []
for base in sorted(glob.glob("/sys/class/powercap/*")):
    entry = {"path": base}
    for name in ("name", "energy_uj", "max_energy_range_uj", "power_uw", "enabled"):
        path = os.path.join(base, name)
        if os.path.isfile(path):
            value = read_text(path)
            entry[name] = int(value) if value and value.isdigit() else value
    powercap.append(entry)

report = {
    "meta": {"collected_at": "$STAMP", "hostname": "$HOST"},
    "commands": {
        "pveversion": run(["pveversion"]),
        "sensors_jA": run(["sensors", "-jA"]),
        "pve_hwinfo": run(["/usr/local/bin/pve-hwinfo.sh"]),
        "pvesh_cpufreq_dry": run(["pvesh", "help", "/nodes/$(hostname -s)/cpufreq"]),
    },
    "sysfs": {
        "cpus": cpus,
        "powercap": powercap,
    },
    "api": {
        "health": fetch_json("http://127.0.0.1:8087/health"),
        "status_legacy": fetch_json("http://127.0.0.1:8087/status"),
        "status_v1": fetch_json("http://127.0.0.1:8087/api/v1/status"),
        "capabilities": fetch_json("http://127.0.0.1:8087/api/v1/capabilities"),
        "profiles": fetch_json("http://127.0.0.1:8087/api/v1/profiles"),
    },
    "nodes_pm": {
        "cpufreq_blocks": int(subprocess.check_output(
            "grep -c \"name => 'cpufreq'\" /usr/share/perl5/PVE/API2/Nodes.pm || true",
            shell=True,
            text=True,
        ).strip() or 0),
        "cpufreq_context": subprocess.check_output(
            "grep -B5 \"name => 'cpufreq'\" /usr/share/perl5/PVE/API2/Nodes.pm | head -20",
            shell=True,
            text=True,
        ),
    },
}

print(json.dumps(report, indent=2))
PY
