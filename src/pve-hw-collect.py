#!/usr/bin/env python3
"""Collect hardware state from sysfs, lm-sensors, and powercap.

Output: JSON on stdout.
  --compact   smaller JSON export
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
from pathlib import Path
from typing import Any

_VERSION_FILES = (
    Path("/usr/share/pve-node-hw-api/VERSION"),
    Path(__file__).resolve().parent.parent / "VERSION",
)


def package_version() -> str:
    for path in _VERSION_FILES:
        if path.is_file():
            return path.read_text(encoding="utf-8").strip()
    return "0.0.0"


VERSION = package_version()


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


def _zone_power_w(zone: dict[str, Any], *, sample_energy: bool) -> float | None:
    pu = zone.get("power_uw")
    if isinstance(pu, int) and pu > 0:
        return round(pu / 1_000_000, 2)
    if not sample_energy:
        return None
    energy_path = os.path.join(zone["path"], "energy_uj")
    if not os.path.isfile(energy_path):
        return None
    e1 = read_int(energy_path)
    t1 = time.monotonic()
    time.sleep(0.12)
    e2 = read_int(energy_path)
    t2 = time.monotonic()
    if e1 is None or e2 is None or t2 <= t1:
        return None
    de = e2 - e1
    if de < 0:
        de += read_int(os.path.join(zone["path"], "max_energy_range_uj")) or 0
    return round((de / (t2 - t1)) / 1_000_000, 2)


def _parse_tdp_w(cpu: dict[str, Any], processor_dmi: dict[str, str], system: dict[str, Any]) -> float:
    for key in ("Max Power", "Maximum Power", "TDP"):
        val = (processor_dmi or {}).get(key, "")
        m = re.search(r"(\d+)\s*W", val, re.I)
        if m:
            return float(m.group(1))
    model = (system or {}).get("processor") or info_get("model name") or ""
    m = re.search(r"(\d{2,3})\s*W", model, re.I)
    if m:
        return float(m.group(1))
    cores = int(cpu.get("online") or cpu.get("total") or 1)
    freq = cpu.get("frequency") or {}
    mhz = freq.get("hw_max_mhz") or freq.get("max_mhz") or 3000
    if not isinstance(mhz, int):
        mhz = 3000
    return float(min(280, max(35, cores * mhz / 1000 * 10)))


def _memory_size_gib(size_text: str) -> float:
    m = re.match(r"^([\d.]+)\s*([KMGT])i?B", (size_text or "").strip(), re.I)
    if not m:
        return 0.0
    n = float(m.group(1))
    mult = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    return n * mult.get(m.group(2).upper(), 1024**3) / (1024**3)


def estimate_system_power(
    *,
    cpu: dict[str, Any],
    memory_modules: list[dict[str, Any]],
    storage: list[dict[str, Any]],
    processor_dmi: dict[str, str],
    system: dict[str, Any],
    rapl_breakdown: list[dict[str, Any]],
) -> dict[str, Any]:
    tdp = _parse_tdp_w(cpu, processor_dmi, system)
    mem_gib = sum(_memory_size_gib(m.get("size", "")) for m in (memory_modules or []))
    memory_w = round(max(4.0, mem_gib * 0.35), 1)
    storage_w = 0.0
    for disk in storage or []:
        storage_w += 7.0 if disk.get("rotational") == "1" else 3.5
    storage_w = round(storage_w, 1)
    platform_w = 25.0
    cores = int(cpu.get("online") or cpu.get("total") or 1)
    load1 = float((system or {}).get("loadavg", [0.0])[0] or 0)
    load_factor = min(1.0, load1 / max(cores, 1))
    cpu_idle_frac = 0.25
    cpu_at_load = round(tdp * (cpu_idle_frac + (1 - cpu_idle_frac) * load_factor), 1)
    plimit = None
    for item in rapl_breakdown:
        if item.get("plimit_w"):
            plimit = item["plimit_w"]
            break
    return {
        "cpu_tdp_w": tdp,
        "cpu_plimit_w": plimit,
        "memory_w": memory_w,
        "storage_w": storage_w,
        "platform_w": platform_w,
        "load_factor": round(load_factor, 2),
        "cpu_at_load_w": cpu_at_load,
        "idle_total_w": round(platform_w + memory_w + storage_w + tdp * cpu_idle_frac, 1),
        "load_total_w": round(platform_w + memory_w + storage_w + cpu_at_load, 1),
    }


def collect_powercap(
    *,
    sensors_normalized: dict[str, Any] | None = None,
    cpu: dict[str, Any] | None = None,
    memory_modules: list[dict[str, Any]] | None = None,
    storage: list[dict[str, Any]] | None = None,
    platform: dict[str, Any] | None = None,
    system: dict[str, Any] | None = None,
    live: bool = False,
) -> dict[str, Any]:
    zones = []
    rapl_breakdown = []
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
        pw = _zone_power_w(zone, sample_energy=not live)
        if pw is not None:
            zone["power_w"] = pw
        plimit = zone.get("constraint_0_power_limit_uw")
        if isinstance(plimit, int) and plimit > 0:
            zone["plimit_w"] = round(plimit / 1_000_000, 1)
        zones.append(zone)
        name_l = (zone.get("name") or "").lower()
        if pw is not None and ("package" in name_l or "dram" in name_l or "core" in name_l or "psys" in name_l):
            rapl_breakdown.append({
                "name": zone.get("name") or path,
                "power_w": pw,
                "plimit_w": zone.get("plimit_w"),
            })

    package_watts = None
    for z in zones:
        if "package" in (z.get("name") or "").lower():
            package_watts = z.get("power_w")
            if package_watts is not None:
                break
    if package_watts is None and rapl_breakdown:
        package_watts = rapl_breakdown[0].get("power_w")

    sensor_power = (sensors_normalized or {}).get("power") or []
    sensor_total = round(sum(p.get("value_w", 0) for p in sensor_power if isinstance(p.get("value_w"), (int, float))), 2)
    rapl_measured = round(sum(r["power_w"] for r in rapl_breakdown if r.get("power_w") is not None), 2)

    cpu = cpu or {}
    estimate = estimate_system_power(
        cpu=cpu,
        memory_modules=memory_modules or [],
        storage=storage or [],
        processor_dmi=(platform or {}).get("processor_dmi") or {},
        system=system or {},
        rapl_breakdown=rapl_breakdown,
    )

    measured_parts = []
    if rapl_measured > 0:
        measured_parts.append(rapl_measured)
    if sensor_total > 0 and sensor_total > rapl_measured * 0.5:
        measured_parts.append(sensor_total)
    measured_total = round(sum(measured_parts), 2) if measured_parts else None

    if measured_total and measured_total > 10:
        display_w = measured_total
        method = "measured"
        confidence = "medium" if len(rapl_breakdown) > 1 or sensor_total else "low"
    else:
        display_w = estimate["load_total_w"]
        method = "estimated"
        confidence = "low"

    if measured_total and method == "measured":
        # Add non-CPU estimate for rest of platform if RAPL is CPU-only
        if rapl_measured and rapl_measured < estimate["load_total_w"] * 0.6:
            display_w = round(rapl_measured + estimate["memory_w"] + estimate["storage_w"] + estimate["platform_w"], 1)
            method = "hybrid"
            confidence = "medium"

    return {
        "zones": zones,
        "package_watts": package_watts,
        "rapl_breakdown": rapl_breakdown,
        "rapl_measured_w": rapl_measured or None,
        "sensor_power": sensor_power,
        "sensor_total_w": sensor_total or None,
        "measured_total_w": measured_total,
        "estimate": estimate,
        "system_watts": display_w,
        "method": method,
        "confidence": confidence,
    }


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


# Appended to pve-hw-collect.py - merged by build script

def collect_block() -> list[dict[str, Any]]:
    data = run_json([
        "lsblk", "-J", "-o",
        "NAME,MODEL,SIZE,TYPE,ROTA,TRAN,REV,SERIAL,MOUNTPOINTS",
    ])
    if not isinstance(data, dict):
        return []
    return data.get("blockdevices") or []


def _flatten_disks(blockdevices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    disks = []

    def walk(nodes, parents=None):
        parents = parents or []
        for node in nodes or []:
            if not isinstance(node, dict):
                continue
            name = node.get("name")
            children = node.get("children") or []
            if node.get("type") == "disk":
                disks.append({**node, "parents": parents[:]})
            if children:
                walk(children, parents + ([name] if name else []))

    walk(blockdevices)
    return disks


def _smartctl_json(path: str) -> dict[str, Any]:
    if not shutil.which("smartctl"):
        return {}
    for args in (["-j", "-a", path], ["-j", "-i", path]):
        proc = subprocess.run(
            ["smartctl", *args],
            capture_output=True,
            text=True,
            timeout=12,
            check=False,
        )
        if proc.stdout.strip():
            try:
                return json.loads(proc.stdout)
            except Exception:
                pass
    return {}


def collect_storage() -> list[dict[str, Any]]:
    disks = []
    for node in _flatten_disks(collect_block()):
        name = node.get("name")
        if not name:
            continue
        path = f"/dev/{name}"
        smart = _smartctl_json(path)
        nvme = smart.get("nvme_smart_health_information_log") or {}
        temp = nvme.get("temperature")
        wear = nvme.get("percent_used")
        hours = nvme.get("power_on_hours")
        data_read_u = nvme.get("data_units_read")
        data_written_u = nvme.get("data_units_written")
        data_read_gib = _nvme_units_to_gib(data_read_u)
        data_written_gib = _nvme_units_to_gib(data_written_u)
        for item in (smart.get("ata_smart_attributes") or {}).get("table") or []:
            label = (item.get("name") or "").lower()
            raw_val = item.get("raw", {}).get("value")
            if label == "temperature_celsius" and temp is None:
                temp = raw_val
            if label == "power_on_hours":
                hours = hours or raw_val
            if label == "total_lbas_written":
                data_written_gib = data_written_gib or _lba_sectors_to_gib(raw_val)
            if label == "total_lbas_read":
                data_read_gib = data_read_gib or _lba_sectors_to_gib(raw_val)
        queue = f"/sys/block/{name}/queue"
        disks.append({
            "name": name,
            "path": path,
            "model": node.get("model") or smart.get("model_name"),
            "serial": node.get("serial") or smart.get("serial_number"),
            "size_bytes": node.get("size"),
            "transport": node.get("tran"),
            "rotational": node.get("rota"),
            "revision": node.get("rev"),
            "mountpoints": node.get("mountpoints"),
            "temperature_c": temp,
            "wear_percent": wear,
            "power_on_hours": hours,
            "data_read_gib": data_read_gib,
            "data_written_gib": data_written_gib,
            "scheduler": read_text(os.path.join(queue, "scheduler")) if os.path.isdir(queue) else "",
            "read_ahead_kb": read_int(os.path.join(queue, "read_ahead_kb")),
            "max_sectors_kb": read_int(os.path.join(queue, "max_sectors_kb")),
        })
    return disks


def collect_diskstats() -> list[dict[str, Any]]:
    text = read_text("/proc/diskstats")
    if not text:
        return []
    stats = []
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 14 or not parts[2]:
            continue
        name = parts[2]
        if name.startswith(("loop", "ram", "dm-")):
            continue
        rd_sectors = int(parts[5])
        wr_sectors = int(parts[9])
        stats.append({
            "device": name,
            "reads_completed": int(parts[3]),
            "writes_completed": int(parts[7]),
            "read_mib": round(rd_sectors * 512 / (1024 * 1024), 2),
            "write_mib": round(wr_sectors * 512 / (1024 * 1024), 2),
        })
    return stats


def _dmidecode_records(dtype: str) -> list[dict[str, str]]:
    if not shutil.which("dmidecode"):
        return []
    proc = subprocess.run(["dmidecode", "-t", dtype], capture_output=True, text=True, timeout=8, check=False)
    if proc.returncode != 0:
        return []
    records, current = [], {}
    for line in proc.stdout.splitlines():
        if line.startswith("Handle "):
            if current:
                records.append(current)
            current = {}
        elif ":" in line:
            k, v = line.split(":", 1)
            current[k.strip()] = v.strip()
    if current:
        records.append(current)
    return records


def collect_platform() -> dict[str, Any]:
    pci = []
    if shutil.which("lspci"):
        proc = subprocess.run(["lspci"], capture_output=True, text=True, timeout=5, check=False)
        if proc.returncode == 0:
            pci = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()][:20]
    return {
        "system": (_dmidecode_records("system") or [{}])[0],
        "baseboard": (_dmidecode_records("baseboard") or [{}])[0],
        "bios": (_dmidecode_records("bios") or [{}])[0],
        "processor_dmi": (_dmidecode_records("processor") or [{}])[0],
        "pci_summary": pci,
    }


def collect_memory_modules() -> list[dict[str, Any]]:
    modules = []
    for rec in _dmidecode_records("memory"):
        size = rec.get("Size", "")
        if not size or "no module" in size.lower():
            continue
        modules.append({
            "locator": rec.get("Locator"),
            "size": size,
            "type": rec.get("Type"),
            "speed": rec.get("Speed") or rec.get("Configured Memory Speed"),
            "manufacturer": rec.get("Manufacturer"),
            "part_number": rec.get("Part Number"),
        })
    return modules


_NET_ARPHRD = {
    1: "Ethernet",
    772: "Wi-Fi",
    32: "InfiniBand",
    512: "PPP",
    768: "IPIP",
    65534: "Tunnel",
}


def _network_iface_kind(name: str, path: str) -> str:
    if os.path.isdir(os.path.join(path, "wireless")):
        return "Wi-Fi"
    type_id = read_int(os.path.join(path, "type"))
    if type_id in _NET_ARPHRD:
        return _NET_ARPHRD[type_id]
    lower = name.lower()
    if lower.startswith(("wlan", "wlp", "wl")):
        return "Wi-Fi"
    if lower.startswith(("eth", "enp", "eno", "ens", "em", "p")):
        return "Ethernet"
    if lower.startswith(("br", "docker", "virbr")):
        return "Bridge"
    if lower.startswith(("bond", "team")):
        return "Bond"
    return "Network"


def _network_subgroup_title(iface: dict[str, Any]) -> str:
    parts = [iface.get("name") or "?"]
    if iface.get("kind"):
        parts.append(str(iface["kind"]))
    if iface.get("driver"):
        parts.append(str(iface["driver"]))
    return " · ".join(parts)


def _network_iface_rows(iface: dict[str, Any]) -> list[dict[str, Any]]:
    eth = iface.get("ethtool") or {}
    max_speed = eth.get("Supported link modes") or eth.get("Speed")
    if not max_speed and iface.get("speed_mbps"):
        max_speed = f"{iface['speed_mbps']} Mbps"
    cur_speed = eth.get("Speed")
    if not cur_speed and iface.get("speed_mbps"):
        cur_speed = f"{iface['speed_mbps']} Mbps"
    rows = [
        _row("Kind", "detected", iface.get("kind"), "sysfs"),
        _row("MAC", "hardware", iface.get("mac"), "sysfs"),
        _row("Operstate", "up / down", iface.get("operstate"), "sysfs"),
        _row("Link", "carrier", "up" if iface.get("carrier") == 1 else "down", "sysfs"),
        _row("Speed", max_speed or "—", cur_speed or "—", "ethtool"),
        _row("Duplex", "full / half", iface.get("duplex") or eth.get("Duplex") or "—", "ethtool"),
        _row("Driver", iface.get("driver"), iface.get("driver"), "ethtool"),
    ]
    if iface.get("wireless_mode"):
        rows.append(_row("Wireless mode", "802.11", iface.get("wireless_mode"), "sysfs"))
    return rows


def collect_network() -> list[dict[str, Any]]:
    interfaces = []
    skip_exact = {"lo", "bonding_masters"}
    skip_prefixes = ("veth", "fwbr", "fwpr", "tap", "vmbr")
    for iface in sorted(os.listdir("/sys/class/net")):
        if iface in skip_exact or iface.startswith(skip_prefixes):
            continue
        path = f"/sys/class/net/{iface}"
        ethtool = {}
        if shutil.which("ethtool"):
            proc = subprocess.run(["ethtool", iface], capture_output=True, text=True, timeout=4, check=False)
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        ethtool[k.strip()] = v.strip()
        kind = _network_iface_kind(iface, path)
        wireless_mode = None
        wmode = read_text(os.path.join(path, "wireless", "mode"))
        if wmode:
            wireless_mode = wmode
        interfaces.append({
            "name": iface,
            "kind": kind,
            "mac": read_text(os.path.join(path, "address")),
            "carrier": read_int(os.path.join(path, "carrier")),
            "speed_mbps": read_int(os.path.join(path, "speed")),
            "duplex": read_text(os.path.join(path, "duplex")),
            "operstate": read_text(os.path.join(path, "operstate")),
            "driver": ethtool.get("driver"),
            "wireless_mode": wireless_mode,
            "ethtool": ethtool,
        })
    kind_order = {"Ethernet": 0, "Wi-Fi": 1, "InfiniBand": 2, "Bond": 3, "Bridge": 4, "Network": 5}
    interfaces.sort(key=lambda item: (kind_order.get(item.get("kind") or "", 9), item.get("name") or ""))
    return interfaces



def _nvme_units_to_gib(units: Any) -> float | None:
    if units is None:
        return None
    try:
        return int(units) * 512000 / (1024 ** 3)
    except (TypeError, ValueError):
        return None


def _lba_sectors_to_gib(sectors: Any, sector_size: int = 512) -> float | None:
    if sectors is None:
        return None
    try:
        return int(sectors) * sector_size / (1024 ** 3)
    except (TypeError, ValueError):
        return None


def _fmt_gib(gib: float | None) -> str:
    if gib is None:
        return "—"
    if gib >= 1024:
        return f"{gib / 1024:.2f} TiB"
    return f"{gib:.1f} GiB"


def _fmt_size_gib(value: Any) -> str:
    if value is None or value == "":
        return "—"
    text = str(value).strip()
    m = re.match(r"^([\d.]+)\s*([KMGT])i?B?$", text, re.I)
    if m:
        num = float(m.group(1))
        unit = m.group(2).upper()
        mult = {"K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
        return _fmt_gib(num * mult[unit] / (1024**3))
    try:
        return _fmt_gib(int(text) / (1024**3))
    except ValueError:
        return text


def _fmt_mib_to_gib(mib: Any) -> str:
    if mib is None or mib == "" or mib == "?":
        return "—"
    try:
        return _fmt_gib(float(mib) / 1024)
    except (TypeError, ValueError):
        return str(mib)


def _fmt_power_on_hours(hours: Any) -> str:
    if hours is None:
        return "—"
    try:
        h = int(hours)
        return f"{h} h ({round(h / 24 / 365.25, 1)} yr)"
    except (TypeError, ValueError):
        return str(hours)

def _fmt_cell(value: Any) -> str:
    if value is None or value == "" or value == []:
        return "—"
    return str(value)


def _row(param: str, available: Any = None, applied: Any = None, source: str = "") -> dict[str, Any]:
    applied_val = _fmt_cell(applied)
    return {
        "parameter": param,
        "available": _fmt_cell(available),
        "applied": applied_val,
        "source": source,
        "current": applied_val,
    }


def _parse_io_scheduler(raw: str | None) -> tuple[str, str]:
    text = (raw or "").strip()
    if not text:
        return "—", "—"
    applied = "—"
    options: list[str] = []
    for token in text.split():
        if token.startswith("[") and token.endswith("]"):
            applied = token.strip("[]")
        else:
            options.append(token.strip("[]"))
    available = ", ".join(dict.fromkeys(options)) if options else applied
    return available, applied


def _mhz_range(lo: Any, hi: Any, suffix: str = "MHz") -> str:
    if lo is None and hi is None:
        return "—"
    return f"{lo or '?'}–{hi or '?'} {suffix}"


def build_inventory(data: dict[str, Any]) -> list[dict[str, Any]]:
    sections = []
    cpu = data.get("cpu") or {}
    freq = cpu.get("frequency") or {}
    sysinfo = data.get("system") or {}
    lscpu = (data.get("lscpu") or {}).get("lscpu") or {}
    model = lscpu.get("model_name") or sysinfo.get("processor")
    govs = ", ".join(freq.get("available_governors") or [])
    avail_mhz = freq.get("available_frequencies_mhz") or []
    if avail_mhz:
        freq_avail = ", ".join(str(m) for m in avail_mhz) + " MHz"
    else:
        freq_avail = _mhz_range(freq.get("hw_min_mhz"), freq.get("hw_max_mhz"), "MHz (HW)")

    sections.append({
        "id": "cpu",
        "title": "CPU",
        "rows": [
            _row("Model", model, model, "lscpu"),
            _row("Architecture", lscpu.get("architecture"), lscpu.get("architecture"), "lscpu"),
            _row("Logical CPUs", cpu.get("total"), f"{cpu.get('online', '?')} online", "sysfs"),
            _row("Governor", govs or "—", freq.get("governor"), "sysfs"),
            _row("Frequency", freq_avail, f"{freq.get('current_mhz', '?')} MHz", "sysfs"),
            _row("Scaling max", _mhz_range(freq.get("min_mhz"), freq.get("max_mhz")), f"{freq.get('max_mhz', '?')} MHz", "sysfs"),
            _row("HW limits", _mhz_range(freq.get("hw_min_mhz"), freq.get("hw_max_mhz")), f"{freq.get('current_mhz', '?')} MHz (now)", "sysfs"),
            _row("Driver", freq.get("driver"), freq.get("driver"), "sysfs"),
        ],
    })

    mem = data.get("memory") or {}
    total_gib = round((mem.get("MemTotal") or 0) / 1024 / 1024, 1)
    free_gib = round((mem.get("MemAvailable") or 0) / 1024 / 1024, 1)
    used_gib = round(max(total_gib - free_gib, 0), 1)
    mem_rows = [
        _row("RAM", f"{total_gib} GiB installed", f"{free_gib} GiB free, {used_gib} GiB used", "meminfo"),
    ]
    for mod in data.get("memory_modules") or []:
        spec = f"{mod.get('size')} {mod.get('type', '')} @ {mod.get('speed', '')} ({mod.get('manufacturer', '')})"
        mem_rows.append(_row(f"DIMM {mod.get('locator', '?')}", spec, "installed", "dmidecode"))
    sections.append({"id": "memory", "title": "Memory", "rows": mem_rows})

    diskstats = {d["device"]: d for d in (data.get("diskstats") or [])}
    for disk in data.get("storage") or []:
        name = disk.get("name")
        ds = diskstats.get(name) or {}
        sched_avail, sched_applied = _parse_io_scheduler(disk.get("scheduler"))
        sections.append({
            "id": f"disk-{name}",
            "title": f"Storage: {name}",
            "rows": [
                _row("Model", disk.get("model"), disk.get("model"), "smart"),
                _row("Serial", disk.get("serial"), disk.get("serial"), "smart"),
                _row("Bus / type", disk.get("transport"), "rotational" if disk.get("rotational") == "1" else "SSD/NVMe", "lsblk"),
                _row("Capacity", _fmt_size_gib(disk.get("size_bytes")), _fmt_size_gib(disk.get("size_bytes")), "lsblk"),
                _row("Temperature", "SMART / NVMe health", f"{disk.get('temperature_c')} °C" if disk.get("temperature_c") is not None else None, "smart"),
                _row("Wear", "100 % (new)", f"{disk.get('wear_percent')} %" if disk.get("wear_percent") is not None else None, "smart"),
                _row(
                    "Power-on hours",
                    "hours (SMART)",
                    _fmt_power_on_hours(disk.get("power_on_hours")),
                    "smart",
                ),
                _row(
                    "Written (lifetime)",
                    "SMART total",
                    _fmt_gib(disk.get("data_written_gib")),
                    "smart",
                ),
                _row(
                    "Read (lifetime)",
                    "SMART total",
                    _fmt_gib(disk.get("data_read_gib")),
                    "smart",
                ),
                _row("IO scheduler", sched_avail, sched_applied, "sysfs"),
                _row("Total read", "since boot", _fmt_mib_to_gib(ds.get("read_mib")), "diskstats"),
                _row("Total written", "since boot", _fmt_mib_to_gib(ds.get("write_mib")), "diskstats"),
            ],
        })

    plat = data.get("platform") or {}
    board = f"{(plat.get('baseboard') or {}).get('Manufacturer', '?')} {(plat.get('baseboard') or {}).get('Product Name', '')}".strip()
    bios = f"{(plat.get('bios') or {}).get('Version', '?')} ({(plat.get('bios') or {}).get('Release Date', '?')})"
    sections.append({
        "id": "platform",
        "title": "Platform",
        "rows": [
            _row("Board", board, board, "dmidecode"),
            _row("BIOS", bios, bios, "dmidecode"),
            _row("Kernel", "running", sysinfo.get("kernel"), "system"),
            _row("PVE", "installed", sysinfo.get("pveversion"), "pveversion"),
        ],
    })

    network_ifaces = data.get("network") or []
    if network_ifaces:
        sections.append({
            "id": "network",
            "title": "Network",
            "subgroups": [
                {
                    "id": iface.get("name") or f"iface-{idx}",
                    "title": _network_subgroup_title(iface),
                    "rows": _network_iface_rows(iface),
                }
                for idx, iface in enumerate(network_ifaces)
            ],
        })

    sens = (data.get("sensors") or {}).get("normalized") or {}
    if sens.get("temperatures"):
        sections.append({
            "id": "temps",
            "title": "Temperatures",
            "rows": [
                _row(t.get("label") or t.get("chip"), "sensor", f"{t.get('value_c')} °C", "sensors")
                for t in sens["temperatures"][:12]
            ],
        })
    pwr = data.get("power") or {}
    if pwr.get("system_watts") is not None or pwr.get("package_watts") is not None:
        est = pwr.get("estimate") or {}
        method = pwr.get("method") or "?"
        conf = pwr.get("confidence") or "?"
        rows = [
            _row(
                "System total",
                f"{method} ({conf})",
                f"{pwr.get('system_watts')} W",
                "rapl+est",
            ),
        ]
        if pwr.get("package_watts") is not None:
            rows.append(_row("CPU package", "RAPL", f"{pwr.get('package_watts')} W", "rapl"))
        for item in (pwr.get("rapl_breakdown") or []):
            n = (item.get("name") or "").lower()
            if "package" in n:
                continue
            if item.get("power_w") is not None:
                rows.append(_row(item.get("name") or "RAPL zone", "RAPL", f"{item.get('power_w')} W", "rapl"))
        if est.get("memory_w"):
            rows.append(_row("Memory", "estimate", f"{est.get('memory_w')} W", "dmidecode"))
        if est.get("storage_w"):
            rows.append(_row("Storage", "estimate", f"{est.get('storage_w')} W", "inventory"))
        if est.get("platform_w"):
            rows.append(_row("Platform", "estimate", f"{est.get('platform_w')} W", "heuristic"))
        if est.get("cpu_tdp_w"):
            rows.append(_row("CPU TDP", "spec / DMI", f"{est.get('cpu_tdp_w')} W", "estimate"))
        if est.get("cpu_at_load_w"):
            rows.append(_row("CPU @ load", f"load {est.get('load_factor')}", f"{est.get('cpu_at_load_w')} W", "estimate"))
        if est.get("idle_total_w"):
            rows.append(_row("Est. idle total", "heuristic", f"{est.get('idle_total_w')} W", "estimate"))
        for sp in (pwr.get("sensor_power") or [])[:4]:
            rows.append(_row(sp.get("label") or "Sensor", "power", f"{sp.get('value_w')} W", "sensors"))
        sections.append({"id": "power", "title": "Power", "rows": rows})
    return sections



CACHE_DIR = Path("/var/cache/pve-hw-dashboard")
STATIC_CACHE = CACHE_DIR / "static.json"
LIVE_SMART_INTERVAL = 30


def save_static_cache(payload: dict[str, Any]) -> None:
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        static = {
            "saved_at": int(time.time()),
            "smart_refreshed": int(time.time()),
            "lscpu": payload.get("lscpu"),
            "platform": payload.get("platform"),
            "memory_modules": payload.get("memory_modules"),
            "storage": payload.get("storage"),
        }
        STATIC_CACHE.write_text(json.dumps(static, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def load_static_cache() -> dict[str, Any] | None:
    try:
        if STATIC_CACHE.is_file():
            return json.loads(STATIC_CACHE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    return None


def _disk_temp_sysfs(name: str) -> int | None:
    m = re.match(r"(nvme\d+)", name or "")
    if m:
        nvme = m.group(1)
        for path in sorted(glob.glob(f"/sys/class/nvme/{nvme}/hwmon/hwmon*/temp*_input")):
            val = read_int(path)
            if val and val > 0:
                return int(val / 1000) if val > 200 else val
    for path in sorted(glob.glob(f"/sys/block/{name}/device/hwmon/hwmon*/temp*_input")):
        val = read_int(path)
        if val and val > 0:
            return int(val / 1000) if val > 200 else val
    return None


def collect_storage_live(cached: list[dict[str, Any]], refresh_smart: bool) -> list[dict[str, Any]]:
    if refresh_smart or not cached:
        return collect_storage()
    disks = []
    for disk in cached:
        name = disk.get("name")
        if not name:
            continue
        row = dict(disk)
        queue = f"/sys/block/{name}/queue"
        if os.path.isdir(queue):
            row["scheduler"] = read_text(os.path.join(queue, "scheduler")) or row.get("scheduler")
        temp = _disk_temp_sysfs(name)
        if temp is not None:
            row["temperature_c"] = temp
        disks.append(row)
    return disks


def collect_system_live() -> dict[str, Any]:
    load1, load5, load15 = os.getloadavg()
    uptime = read_float("/proc/uptime")
    return {
        "hostname": socket.gethostname(),
        "kernel": platform.release(),
        "loadavg": [load1, load5, load15],
        "uptime_seconds": int(uptime) if uptime else None,
    }


def collect_live() -> dict[str, Any]:
    static = load_static_cache() or {}
    smart_at = int(static.get("smart_refreshed") or 0)
    refresh_smart = (not static.get("storage")) or (int(time.time()) - smart_at >= LIVE_SMART_INTERVAL)
    cpu = collect_cpus()
    storage = collect_storage_live(static.get("storage") or [], refresh_smart)
    if refresh_smart and storage:
        static = {**static, "storage": storage, "smart_refreshed": int(time.time())}
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            STATIC_CACHE.write_text(json.dumps(static, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    sensors = collect_sensors()
    system = collect_system_live()
    payload = {
        "meta": {
            "name": "Proxmox Node Hardware API",
            "version": VERSION,
            "collected_at": int(time.time()),
            "mode": "live",
        },
        "system": system,
        "cpu": cpu,
        "sensors": sensors,
        "power": collect_powercap(
            sensors_normalized=(sensors.get("normalized") or {}),
            cpu=cpu,
            memory_modules=static.get("memory_modules") or collect_memory_modules(),
            storage=storage,
            platform=static.get("platform") or collect_platform(),
            system=system,
            live=True,
        ),
        "memory": collect_memory(),
        "diskstats": collect_diskstats(),
        "network": collect_network(),
        "storage": storage,
        "lscpu": static.get("lscpu") or collect_lscpu(),
        "platform": static.get("platform") or collect_platform(),
        "memory_modules": static.get("memory_modules") or collect_memory_modules(),
        "capabilities": collect_capabilities(cpu),
        "profiles": profile_catalog(cpu),
        "warnings": collect_warnings(cpu),
    }
    payload["inventory"] = build_inventory(payload)
    return payload


def wrap_compact_legacy(data: dict[str, Any]) -> dict[str, Any]:
    cpu = data.get("cpu") or {}
    sens = (data.get("sensors") or {}).get("normalized") or {}
    return {
        "meta": data.get("meta"),
        "cpu": cpu,
        "sensors": {
            "temperatures": sens.get("temperatures", [])[:12],
            "fans": sens.get("fans", [])[:8],
        },
        "power": data.get("power") or {},
        "capabilities": data.get("capabilities"),
        "profiles": data.get("profiles"),
        "cpufreq": {
            "governor": (cpu.get("frequency") or {}).get("governor"),
            "available_governors": (cpu.get("frequency") or {}).get("available_governors"),
            "scaling_cur_freq": (cpu.get("frequency") or {}).get("current_khz"),
            "scaling_min_freq": (cpu.get("frequency") or {}).get("min_khz"),
            "scaling_max_freq": (cpu.get("frequency") or {}).get("max_khz"),
            "cpuinfo_min_freq": (cpu.get("frequency") or {}).get("hw_min_khz"),
            "cpuinfo_max_freq": (cpu.get("frequency") or {}).get("hw_max_khz"),
            "available_frequencies": (cpu.get("frequency") or {}).get("available_frequencies_khz"),
            "per_core_freq": [m * 1000 for m in (cpu.get("frequency") or {}).get("per_core_mhz", []) if m],
        },
        "cpus": {"online": cpu.get("online"), "total": cpu.get("total")},
        "storage": data.get("storage"),
        "diskstats": data.get("diskstats"),
        "platform": data.get("platform"),
        "memory_modules": data.get("memory_modules"),
        "network": data.get("network"),
        "inventory": data.get("inventory"),
    }


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




def collect_warnings(cpu: dict[str, Any] | None = None) -> list[str]:
    warnings: list[str] = []
    if not shutil.which("sensors"):
        warnings.append("lm-sensors not installed; temperature data limited")
    if not shutil.which("smartctl"):
        warnings.append("smartctl not installed; disk SMART metrics unavailable")
    cpu = cpu or {}
    freq = cpu.get("frequency") or {}
    if not freq.get("available_governors"):
        warnings.append("cpufreq governors not exposed in sysfs")
    return warnings

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
    storage = collect_storage()
    platform = collect_platform()
    memory_modules = collect_memory_modules()
    system = collect_system()
    payload = {
        "meta": {
            "name": "Proxmox Node Hardware API",
            "version": VERSION,
            "collected_at": int(time.time()),
        },
        "system": system,
        "cpu": cpu,
        "sensors": sensors,
        "hwmon": collect_hwmon(),
        "power": collect_powercap(
            sensors_normalized=(sensors.get("normalized") or {}),
            cpu=cpu,
            memory_modules=memory_modules,
            storage=storage,
            platform=platform,
            system=system,
            live=False,
        ),
        "memory": collect_memory(),
        "block": collect_block(),
        "storage": storage,
        "diskstats": collect_diskstats(),
        "platform": platform,
        "memory_modules": memory_modules,
        "network": collect_network(),
        "lscpu": collect_lscpu(),
        "capabilities": collect_capabilities(cpu),
        "profiles": profile_catalog(cpu),
        "warnings": collect_warnings(cpu),
    }
    payload["inventory"] = build_inventory(payload)
    save_static_cache(payload)
    return payload


def collect_compact() -> dict[str, Any]:
    return wrap_compact_legacy(collect_live())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    if args.live:
        data = collect_live()
    elif args.compact:
        data = collect_compact()
    else:
        data = collect_full()
    indent = 2 if args.pretty else None
    json.dump(data, sys.stdout, ensure_ascii=False, separators=None if args.pretty else (",", ":"))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
