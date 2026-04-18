#!/usr/bin/env python3
"""Proxmox CPU Dashboard API.

Endpoints:
  GET  /health   - liveness check
  GET  /status   - full hardware state (sensors + cpufreq + power) as flat JSON
  POST /cpufreq  - set CPU governor / max frequency
                   body: governor=<name>&max_freq=<khz>  (application/x-www-form-urlencoded)
                   or   JSON  {"governor": "...", "max_freq": 1700000}

Runs on 0.0.0.0:8087 (managed by pve-cpufreq-api.service).
Called by:
  - the Proxmox Summary UI (pve_node_summary.js, Apply/Presets buttons)
  - the Home Assistant custom integration (proxmox_cpu_ctl)
"""
import glob
import http.server
import json
import os
import subprocess
import threading
import time
import urllib.parse

HWINFO_SCRIPT = "/usr/local/bin/pve-hwinfo.sh"
SETFREQ_SCRIPT = "/usr/local/bin/pve-cpufreq-set.sh"
SETCPUS_SCRIPT = "/usr/local/bin/pve-cpus-set.sh"


def _count_cpus():
    """Return (online_count, total_count) by scanning /sys/devices/system/cpu/."""
    import glob as _g
    total = 0
    online = 0
    has_cpu0 = os.path.isfile("/sys/devices/system/cpu/cpu0/online")
    for path in _g.glob("/sys/devices/system/cpu/cpu[0-9]*/online"):
        total += 1
        try:
            with open(path) as f:
                if f.read().strip() == "1":
                    online += 1
        except Exception:
            pass
    # Directories without online file (usually cpu0) are always online
    all_dirs = _g.glob("/sys/devices/system/cpu/cpu[0-9]*")
    total_dirs = len(all_dirs)
    if not has_cpu0:
        # cpu0 is counted in total_dirs but not in online scan
        online += 1
    total = total_dirs
    return online, total

# -------- RAPL power reader --------

class PowerReader:
    """Read CPU package power via RAPL (AMD or Intel).

    Power is computed as delta(energy_uj) / delta(time). First call returns None;
    subsequent calls return average W since previous call. Thread-safe.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._prev = None  # (energy_uj, ts)
        self._path = self._find_rapl_path()

    @staticmethod
    def _find_rapl_path():
        # Try every powercap entry (AMD or Intel) that exposes energy_uj at package level.
        candidates = sorted(glob.glob("/sys/class/powercap/*/energy_uj"))
        for p in candidates:
            parent = os.path.dirname(p)
            name_file = os.path.join(parent, "name")
            try:
                with open(name_file) as f:
                    name = f.read().strip()
            except Exception:
                name = ""
            # Prefer a package entry; ignore sub-domains (core/uncore/dram).
            if "package" in name.lower() or parent.endswith(":0"):
                return p
        # Fallback: first available energy counter.
        return candidates[0] if candidates else None

    def read_watts(self):
        if not self._path:
            return None
        try:
            with open(self._path) as f:
                energy_uj = int(f.read().strip())
        except Exception:
            return None
        now = time.monotonic()
        with self._lock:
            if self._prev is None:
                self._prev = (energy_uj, now)
                return None
            prev_e, prev_t = self._prev
            dt = now - prev_t
            de = energy_uj - prev_e
            # RAPL counters wrap around; discard negative deltas.
            if dt <= 0 or de < 0:
                self._prev = (energy_uj, now)
                return None
            self._prev = (energy_uj, now)
            # energy_uj is microjoules; W = uJ / us -> divide by 1e6
            return round(de / dt / 1e6, 2)


POWER = PowerReader()

# -------- /status builder --------

def _build_status():
    """Call pve-hwinfo.sh, parse JSON, and flatten for HA consumption."""
    try:
        result = subprocess.run(
            [HWINFO_SCRIPT], capture_output=True, text=True, timeout=5
        )
        hw = json.loads(result.stdout)
    except Exception as e:
        return {"error": f"hwinfo failed: {e}"}

    # Extract temperatures (schema: top-level chip name -> subfeature -> {tempN_input: val})
    temps = {}
    for chip_name, subs in hw.items():
        if chip_name == "cpufreq" or not isinstance(subs, dict):
            continue
        for sub_name, vals in subs.items():
            if not isinstance(vals, dict):
                continue
            for k, v in vals.items():
                if k.endswith("_input") and isinstance(v, (int, float)):
                    key = f"{chip_name}_{sub_name}".lower()
                    # Produce clean keys: k10temp-pci-00c3_tctl -> cpu_tctl etc.
                    if "k10temp" in chip_name.lower() or "coretemp" in chip_name.lower():
                        temps["cpu_tctl"] = round(v, 1)
                    elif "nvme" in chip_name.lower():
                        if "composite" in sub_name.lower():
                            temps["nvme_composite"] = round(v, 1)
                        elif "sensor 1" in sub_name.lower() or "sensor1" in sub_name.lower():
                            temps["nvme_sensor1"] = round(v, 1)
                        else:
                            # Generic fallback: nvme_<subname>
                            temps[key.replace("-pci-", "_").replace(" ", "_")] = round(v, 1)
                    else:
                        temps[key.replace("-pci-", "_").replace(" ", "_")] = round(v, 1)
                    break  # one reading per sub

    cf = hw.get("cpufreq", {}) or {}
    per_core = cf.get("per_core_freq") or []

    power_w = POWER.read_watts()
    cpus_online, cpus_total = _count_cpus()

    return {
        "temps": temps,
        "cpufreq": {
            "current_khz": cf.get("scaling_cur_freq", 0),
            "min_khz": cf.get("scaling_min_freq", 0),
            "max_khz": cf.get("scaling_max_freq", 0),
            "hw_min_khz": cf.get("cpuinfo_min_freq", 0),
            "hw_max_khz": cf.get("cpuinfo_max_freq", 0),
            "governor": cf.get("governor", ""),
            "available_governors": cf.get("available_governors", []),
            "available_frequencies": cf.get("available_frequencies", []),
        },
        "cpus": {"online": cpus_online, "total": cpus_total},
        "power_w": power_w,
        "per_core_mhz": [round(f / 1000) for f in per_core] if per_core else [],
    }


# -------- HTTP handler --------

class Handler(http.server.BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path == "/health":
            self._send_json(200, {"ok": True, "version": "0.3.0"})
        elif path == "/status":
            self._send_json(200, _build_status())
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        path = self.path.split("?", 1)[0]
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length > 0 else ""
        ct = (self.headers.get("Content-Type") or "").lower()

        # Parse body: JSON or urlencoded
        if "json" in ct and raw:
            try:
                params = {k: [str(v)] for k, v in json.loads(raw).items()}
            except Exception:
                params = {}
        else:
            params = urllib.parse.parse_qs(raw)
        # Query string override
        if "?" in self.path:
            params.update(urllib.parse.parse_qs(self.path.split("?", 1)[1]))

        if path == "/cpufreq":
            gov = (params.get("governor", [""])[0] or "").strip()
            freq = (params.get("max_freq", [""])[0] or "").strip()
            try:
                result = subprocess.run(
                    [SETFREQ_SCRIPT, gov, freq],
                    capture_output=True, text=True, timeout=5,
                )
                if result.returncode != 0:
                    self._send_json(400, {
                        "success": False,
                        "error": (result.stderr or result.stdout).strip(),
                    })
                else:
                    self._send_json(200, {
                        "success": True,
                        "message": result.stdout.strip(),
                    })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
        elif path == "/cpus":
            online = (params.get("online", [""])[0] or "").strip()
            if not online.isdigit():
                self._send_json(400, {"success": False, "error": "online must be a positive integer"})
                return
            try:
                result = subprocess.run(
                    [SETCPUS_SCRIPT, online],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    self._send_json(400, {
                        "success": False,
                        "error": (result.stderr or result.stdout).strip(),
                    })
                else:
                    self._send_json(200, {
                        "success": True,
                        "message": result.stdout.strip(),
                    })
            except Exception as e:
                self._send_json(500, {"success": False, "error": str(e)})
        else:
            self._send_json(404, {"error": "not found"})

    def log_message(self, format, *args):
        pass  # silent


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("0.0.0.0", 8087), Handler)
    print("Proxmox CPU Dashboard API listening on 0.0.0.0:8087")
    server.serve_forever()
