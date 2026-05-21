#!/usr/bin/env python3
"""Collect hardware state from sysfs, lm-sensors, and powercap.

Output: JSON on stdout.
  --compact   smaller JSON for Nodes.pm thermalstate field
  --pretty    indented JSON (default for API GET /nodes/{node}/hw)
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
from typing import Any

VERSION = "2.0.0"


def read_text(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read().strip()
    except OSError:
        return None


def read_int(path: str) -> int | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def read_float(path: str) -> float | None:
    text = read_text(path)
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def mhz(khz: int | None) -> int | None:
    return round(khz / 1000) if isinstance(khz, int) and khz > 0 else None


def parse_words(text: str | None) -> list[str]:
    return [w for w in (text or "").split() if w]


def parse_int_words(text: str | None) -> list[int]:
    out = []
    for w in parse_words(text):
        try:
            out.append(int(w))
        except ValueError:
            pass
    return out


def run_json(cmd: list[str], timeout: int = 8) -> Any:
    if not shutil.which(cmd[0]):
        return None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
    except Exception:
        pass
    return None


def cpu_ids() -> list[int]:
    ids = []
    for path in glob.glob("/sys/devices/system/cpu/cpu[0-9]*"):
        name = os.path.basename(path)
        if name.startswith("cpu"):
            try:
                ids.append(int(name[3:]))
            except ValueError:
                pass
    return sorted(ids)


def cpu_online(cpu_id: int) -> bool:
    path = f"/sys/devices/system/cpu/cpu{cpu_id}/online"
    if not os.path.exists(path):
        return cpu_id == 0
    return read_int(path) == 1


def collect_cpufreq(cpu_id: int) -> dict[str, Any]:
    base = f"/sys/devices/system/cpu/cpu{cpu_id}/cpufreq"
    if not os.path.isdir(base):
        return {"available": False}
    gov = read_text(os.path.join(base, "scaling_governor")) or ""
    cur = read_int(os.path.join(base, "scaling_cur_freq"))
    min_f = read_int(os.path.join(base, "scaling_min_freq"))
    max_f = read_int(os.path.join(base, "scaling_max_freq"))
    hw_min = read_int(os.path.join(base, "cpuinfo_min_freq"))
    hw_max = read_int(os.path.join(base, "cpuinfo_max_freq"))
    avail_gov = parse_words(read_text(os.path.join(base, "scaling_available_governors")))
    avail_freq = parse_int_words(read_text(os.path.join(base, "scaling_available_frequencies")))
    return {
        "available": True,
        "current_khz": cur,
        "current_mhz": mhz(cur),
        "min_khz": min_f,
        "min_mhz": mhz(min_f),
        "max_khz": max_f,
        "max_mhz": mhz(max_f),
        "hw_min_khz": hw_min,
        "hw_min_mhz": mhz(hw_min),
        "hw_max_khz": hw_max,
        "hw_max_mhz": mhz(hw_max),
        "governor": gov,
        "driver": read_text(os.path.join(base, "scaling_driver")) or "",
        "available_governors": avail_gov,
        "available_frequencies_khz": avail_freq,
        "available_frequencies_mhz": [mhz(x) for x in avail_freq if mhz(x)],
    }


def collect_cpu_topology(cpu_id: int) -> dict[str, Any]:
    base = f"/sys/devices/system/cpu/cpu{cpu_id}/topology"
    if not os.path.isdir(base):
        return {}
    return {
        "physical_package_id": read_int(os.path.join(base, "physical_package_id")),
        "core_id": read_int(os.path.join(base, "core_id")),
        "thread_siblings_list": read_text(os.path.join(base, "thread_siblings_list")) or "",
        "core_siblings_list": read_text(os.path.join(base, "core_siblings_list")) or "",
    }


def collect_cpus() -> dict[str, Any]:
    per_cpu = []
    for cpu_id in cpu_ids():
        freq = collect_cpufreq(cpu_id)
        online = cpu_online(cpu_id)
        per_cpu.append({
            "id": cpu_id,
            "online": online,
            "topology": collect_cpu_topology(cpu_id),
            "frequency": freq,
        })

    online_ids = [c["id"] for c in per_cpu if c["online"]]
    offline_ids = [c["id"] for c in per_cpu if not c["online"]]
    freq_cpus = [c for c in per_cpu if c["frequency"].get("available")]
    ref = next((c for c in freq_cpus if c["online"]), freq_cpus[0] if freq_cpus else None)
    ref_f = ref["frequency"] if ref else {}
    currents = [
        c["frequency"]["current_khz"]
        for c in freq_cpus
        if c["online"] and isinstance(c["frequency"].get("current_khz"), int)
    ]
    avg_cur = round(sum(currents) / len(currents)) if currents else ref_f.get("current_khz")

    return {
        "total": len(per_cpu),
        "online": len(online_ids),
        "offline": len(offline_ids),
        "online_ids": online_ids,
        "offline_ids": offline_ids,
        "per_cpu": per_cpu,
        "frequency": {
            "available": bool(freq_cpus),
            "current_khz": avg_cur,
            "current_mhz": mhz(avg_cur),
            "min_khz": ref_f.get("min_khz"),
            "min_mhz": ref_f.get("min_mhz"),
            "max_khz": ref_f.get("max_khz"),
            "max_mhz": ref_f.get("max_mhz"),
            "hw_min_khz": ref_f.get("hw_min_khz"),
            "hw_min_mhz": ref_f.get("hw_min_mhz"),
            "hw_max_khz": ref_f.get("hw_max_khz"),
            "hw_max_mhz": ref_f.get("hw_max_mhz"),
            "governor": ref_f.get("governor", ""),
            "driver": ref_f.get("driver", ""),
            "available_governors": ref_f.get("available_governors", []),
            "available_frequencies_khz": ref_f.get("available_frequencies_khz", []),
            "available_frequencies_mhz": ref_f.get("available_frequencies_mhz", []),
            "per_core_mhz": [
                c["frequency"].get("current_mhz")
                for c in freq_cpus
                if isinstance(c["frequency"].get("current_mhz"), int)
            ],
        },
    }


def normalize_sensors(raw: dict[str, Any]) -> dict[str, Any]:
    temps, fans, volts, power, other = [], [], [], [], []
    for chip, labels in (raw or {}).items():
        if chip == "cpufreq" or not isinstance(labels, dict):
            continue
        for label, readings in labels.items():
            if not isinstance(readings, dict):
                continue
            for key, value in readings.items():
                if not isinstance(value, (int, float)):
                    continue
                entry = {"chip": chip, "label": label, "key": key, "value": value}
                if key.endswith("_input") and "temp" in key:
                    temps.append({**entry, "value_c": round(float(value), 1)})
                elif "fan" in key and key.endswith("_input"):
                    fans.append({**entry, "rpm": int(value)})
                elif key.endswith("_input") and "in" in key:
                    volts.append({**entry, "value_v": round(float(value) / 1000, 3)})
                elif "power" in key and key.endswith("_input"):
                    power.append({**entry, "value_w": round(float(value) / 1_000_000, 2)})
                else:
                    other.append(entry)
    return {
        "temperatures": sorted(temps, key=lambda x: (-x["value_c"], x["chip"], x["label"])),
        "fans": sorted(fans, key=lambda x: (-x["rpm"], x["label"])),
        "voltages": volts,
        "power": power,
        "other": other,
    }


def collect_sensors() -> dict[str, Any]:
    raw = run_json(["sensors", "-jA"]) or run_json(["sensors", "-j"]) or {}
    normalized = normalize_sensors(raw)
    return {"raw": raw, "normalized": normalized, "available": bool(raw)}


def collect_hwmon() -> list[dict[str, Any]]:
    devices = []
    for hwmon in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
        name = read_text(os.path.join(hwmon, "name")) or os.path.basename(hwmon)
        entry: dict[str, Any] = {"path": hwmon, "name": name, "labels": {}, "readings": {}}
        for fname in sorted(os.listdir(hwmon)):
            fpath = os.path.join(hwmon, fname)
            if not os.path.isfile(fpath):
                continue
            if fname.endswith("_label"):
                idx = fname.replace("_label", "")
                entry["labels"][idx] = read_text(fpath)
            elif re.search(r"_(input|max|min|crit|alarm)$", fname):
                val = read_text(fpath)
                entry["readings"][fname] = int(val) if val and val.isdigit() else val
        devices.append(entry)
    return devices


def collect_powercap() -> dict[str, Any]:
    zones = []
    for path in sorted(glob.glob("/sys/class/powercap/*")):
        zone: dict[str, Any] = {"path": path, "name": read_text(os.path.join(path, "name")) or ""}
        for key in (
            "energy_uj", "max_energy_range_uj", "power_uw", "enabled",
            "constraint_0_power_limit_uw", "constraint_0_time_window_us",
        ):
            fpath = os.path.join(path, key)
            if os.path.isfile(fpath):
                val = read_text(fpath)
                zone[key] = int(val) if val and val.isdigit() else val
        zones.append(zone)

    package_energy = None
    for z in zones:
        if "package" in (z.get("name") or "").lower() or z["path"].endswith(":0"):
            package_energy = os.path.join(z["path"], "energy_uj")
            if os.path.isfile(package_energy):
                break
            package_energy = None

    watts = None
    if package_energy:
        e1 = read_int(package_energy)
        t1 = time.monotonic()
        time.sleep(0.15)
        e2 = read_int(package_energy)
        t2 = time.monotonic()
        if e1 is not None and e2 is not None and t2 > t1:
            de = e2 - e1
            if de < 0:
                de += read_int(os.path.join(os.path.dirname(package_energy), "max_energy_range_uj")) or 0
            watts = round((de / (t2 - t1)) / 1_000_000, 2)

    return {"zones": zones, "package_watts": watts}


def collect_memory() -> dict[str, Any]:
    mem: dict[str, Any] = {}
    text = read_text("/proc/meminfo")
    if not text:
        return mem
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, val = line.split(":", 1)
        parts = val.strip().split()
        if parts:
            mem[key.strip()] = int(parts[0]) if parts[0].isdigit() else val.strip()
    return mem


def collect_block() -> list[dict[str, Any]]:
    data = run_json(["lsblk", "-J", "-O", "-o", "NAME,MODEL,SIZE,TYPE,ROTA,TRAN,TEMPERATURE,MOUNTPOINTS"])
    if not isinstance(data, dict):
        return []
    return data.get("blockdevices") or []


def collect_lscpu() -> dict[str, Any]:
    info: dict[str, str] = {}
    text = read_text("/proc/cpuinfo")
    if text:
        for line in text.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
    lscpu = run_json(["lscpu", "-J"])
    return {"cpuinfo": info, "lscpu": lscpu}


def collect_system() -> dict[str, Any]:
    load1, load5, load15 = os.getloadavg()
    uptime = read_float("/proc/uptime")
    return {
        "hostname": socket.gethostname(),
        "kernel": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor() or info_get("model name"),
        "loadavg": [load1, load5, load15],
        "uptime_seconds": int(uptime) if uptime else None,
        "pveversion": run_command_text(["pveversion"]),
    }


def info_get(key: str) -> str:
    text = read_text("/proc/cpuinfo") or ""
    for line in text.splitlines():
        if line.lower().startswith(key.lower() + ":"):
            return line.split(":", 1)[1].strip()
    return ""


def run_command_text(cmd: list[str]) -> str | None:
    if not shutil.which(cmd[0]):
        return None
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except Exception:
        pass
    return None


def collect_capabilities(cpu: dict[str, Any]) -> dict[str, Any]:
    freq = cpu.get("frequency") or {}
    return {
        "cpufreq": bool(freq.get("available")),
        "governor": bool(freq.get("available_governors")),
        "max_frequency": bool(freq.get("hw_max_khz")),
        "online_cpus": os.path.exists("/sys/devices/system/cpu/cpu1/online"),
        "sensors": shutil.which("sensors") is not None,
        "powercap": bool(glob.glob("/sys/class/powercap/*/energy_uj")),
        "hwmon": bool(glob.glob("/sys/class/hwmon/hwmon*")),
    }


def profile_catalog(cpu: dict[str, Any]) -> dict[str, Any]:
    freq = cpu.get("frequency") or {}
    hw_min = freq.get("hw_min_khz") or 400000
    hw_max = freq.get("hw_max_khz") or 2900000
    govs = freq.get("available_governors") or ["ondemand", "powersave", "performance"]
    pick = lambda g: g if g in govs else govs[0]

    def pct(p: float) -> int:
        return int(hw_min + (hw_max - hw_min) * p)

    total = cpu.get("total") or 1
    return {
        "performance": {
            "title": "Performance",
            "settings": {"governor": pick("performance"), "max_freq_khz": hw_max, "online_cpus": total},
        },
        "balanced": {
            "title": "Balanced",
            "settings": {"governor": pick("conservative") if "conservative" in govs else pick("ondemand"), "max_freq_khz": pct(0.5), "online_cpus": total},
        },
        "powersave": {
            "title": "Powersave",
            "settings": {"governor": pick("powersave"), "max_freq_khz": pct(0.35), "online_cpus": total},
        },
        "emergency": {
            "title": "Emergency",
            "settings": {"governor": pick("powersave"), "max_freq_khz": hw_min, "online_cpus": max(1, total // 2)},
        },
        "restore": {
            "title": "Restore",
            "settings": {"governor": pick("ondemand"), "max_freq_khz": pct(0.5), "online_cpus": total},
        },
    }


def collect_full() -> dict[str, Any]:
    cpu = collect_cpus()
    sensors = collect_sensors()
    return {
        "meta": {
            "name": "Proxmox CPU Dashboard",
            "version": VERSION,
            "collected_at": int(time.time()),
        },
        "system": collect_system(),
        "cpu": cpu,
        "sensors": sensors,
        "hwmon": collect_hwmon(),
        "power": collect_powercap(),
        "memory": collect_memory(),
        "block": collect_block(),
        "lscpu": collect_lscpu(),
        "capabilities": collect_capabilities(cpu),
        "profiles": profile_catalog(cpu),
    }


def collect_compact() -> dict[str, Any]:
    full = collect_full()
    cpu = full["cpu"]
    sens = full["sensors"]["normalized"]
    return {
        "meta": full["meta"],
        "cpu": cpu,
        "sensors": {
            "temperatures": sens.get("temperatures", [])[:12],
            "fans": sens.get("fans", [])[:8],
        },
        "power": {"package_watts": full["power"].get("package_watts")},
        "capabilities": full["capabilities"],
        "profiles": full["profiles"],
        # legacy fields for older parsers
        "cpufreq": {
            "governor": cpu["frequency"].get("governor"),
            "available_governors": cpu["frequency"].get("available_governors"),
            "scaling_cur_freq": cpu["frequency"].get("current_khz"),
            "scaling_min_freq": cpu["frequency"].get("min_khz"),
            "scaling_max_freq": cpu["frequency"].get("max_khz"),
            "cpuinfo_min_freq": cpu["frequency"].get("hw_min_khz"),
            "cpuinfo_max_freq": cpu["frequency"].get("hw_max_khz"),
            "available_frequencies": cpu["frequency"].get("available_frequencies_khz"),
            "per_core_freq": [m * 1000 for m in cpu["frequency"].get("per_core_mhz", []) if m],
        },
        "cpus": {"online": cpu["online"], "total": cpu["total"]},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    data = collect_compact() if args.compact else collect_full()
    indent = 2 if args.pretty else None
    json.dump(data, sys.stdout, ensure_ascii=False, separators=None if args.pretty else (",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
