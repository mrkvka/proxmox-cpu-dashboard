#!/bin/bash
# Audit sysfs + native PVE hardware API (no legacy :8087).
set -euo pipefail

AUDIT_OUT="${1:-}"
STAMP=$(date -Iseconds)
HOST=$(hostname -s 2>/dev/null || hostname)
NODE="${NODE:-$HOST}"

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

def read_text(path):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return None

def read_int(path):
    value = read_text(path)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None

def run(cmd):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, check=False)
        return {
            "cmd": cmd,
            "returncode": result.returncode,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
        }
    except Exception as err:
        return {"cmd": cmd, "error": str(err)}

def pvesh_json(path):
    out = run(["pvesh", "get", path, "--output-format", "json"])
    if out.get("returncode") != 0:
        return out
    try:
        return {"path": path, "data": json.loads(out["stdout"])}
    except json.JSONDecodeError:
        return {"path": path, "error": "invalid json", "raw": out}

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
    cpus.append({"id": cpu_id, "online": online, "cpufreq": freq})

report = {
    "meta": {"collected_at": "$STAMP", "hostname": "$HOST", "node": "$NODE"},
    "commands": {
        "pveversion": run(["pveversion"]),
        "sensors_jA": run(["sensors", "-jA"]),
        "collect_pretty": run(["/usr/local/bin/pve-hw-collect.py", "--compact"]),
    },
    "sysfs": {"cpus": cpus},
    "pve_api": {
        "hw": pvesh_json(f"/nodes/$NODE/hw"),
        "hwlive": pvesh_json(f"/nodes/$NODE/hwlive"),
    },
    "install": {
        "hardware_pm": os.path.isfile("/usr/share/perl5/PVE/API2/Nodes/Hardware.pm"),
        "hook": int(subprocess.check_output(
            "grep -c 'PVE-HW-DASHBOARD: begin' /usr/share/perl5/PVE/API2/Nodes.pm 2>/dev/null || echo 0",
            shell=True,
            text=True,
        ).strip() or 0),
    },
}

print(json.dumps(report, indent=2))
PY
