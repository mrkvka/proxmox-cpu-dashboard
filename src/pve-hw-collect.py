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

VERSION = "2.1.0"


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
        if temp is None:
            for item in (smart.get("ata_smart_attributes") or {}).get("table") or []:
                label = (item.get("name") or "").lower()
                if label == "temperature_celsius":
                    temp = item.get("raw", {}).get("value")
                if label == "power_on_hours":
                    hours = hours or item.get("raw", {}).get("value")
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


def collect_network() -> list[dict[str, Any]]:
    interfaces = []
    for iface in sorted(os.listdir("/sys/class/net")):
        if iface == "lo" or iface.startswith(("veth", "fwbr", "fwpr", "tap")):
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
        interfaces.append({
            "name": iface,
            "carrier": read_int(os.path.join(path, "carrier")),
            "speed_mbps": read_int(os.path.join(path, "speed")),
            "duplex": read_text(os.path.join(path, "duplex")),
            "operstate": read_text(os.path.join(path, "operstate")),
            "driver": ethtool.get("driver"),
            "ethtool": ethtool,
        })
    return interfaces


def _row(param: str, current: Any, source: str = "") -> dict[str, Any]:
    val = current
    if val is None or val == "" or val == []:
        val = "—"
    return {"parameter": param, "current": val, "source": source}


def build_inventory(data: dict[str, Any]) -> list[dict[str, Any]]:
    sections = []
    cpu = data.get("cpu") or {}
    freq = cpu.get("frequency") or {}
    sysinfo = data.get("system") or {}
    lscpu = (data.get("lscpu") or {}).get("lscpu") or {}

    sections.append({
        "id": "cpu",
        "title": "CPU",
        "rows": [
            _row("Model", lscpu.get("model_name") or sysinfo.get("processor"), "lscpu"),
            _row("Architecture", lscpu.get("architecture"), "lscpu"),
            _row("Cores / threads", f"{cpu.get('online', '?')} online of {cpu.get('total', '?')}", "sysfs"),
            _row("Governor (now)", freq.get("governor"), "sysfs"),
            _row("Frequency (now)", f"{freq.get('current_mhz', '?')} MHz", "sysfs"),
            _row("Max limit (now)", f"{freq.get('max_mhz', '?')} MHz", "sysfs"),
            _row("HW range", f"{freq.get('hw_min_mhz', '?')}–{freq.get('hw_max_mhz', '?')} MHz", "sysfs"),
            _row("Available governors", ", ".join(freq.get("available_governors") or []), "sysfs"),
        ],
    })

    mem = data.get("memory") or {}
    mem_rows = [
        _row("RAM total", f"{round((mem.get('MemTotal') or 0) / 1024 / 1024, 1)} GiB", "meminfo"),
        _row("RAM available", f"{round((mem.get('MemAvailable') or 0) / 1024 / 1024, 1)} GiB", "meminfo"),
    ]
    for mod in data.get("memory_modules") or []:
        mem_rows.append(_row(
            f"DIMM {mod.get('locator', '?')}",
            f"{mod.get('size')} {mod.get('type', '')} @ {mod.get('speed', '')} ({mod.get('manufacturer', '')})",
            "dmidecode",
        ))
    sections.append({"id": "memory", "title": "Memory", "rows": mem_rows})

    diskstats = {d["device"]: d for d in (data.get("diskstats") or [])}
    for disk in data.get("storage") or []:
        name = disk.get("name")
        ds = diskstats.get(name) or {}
        sections.append({
            "id": f"disk-{name}",
            "title": f"Storage: {name}",
            "rows": [
                _row("Model", disk.get("model"), "smart"),
                _row("Serial", disk.get("serial"), "smart"),
                _row("Bus", disk.get("transport"), "lsblk"),
                _row("Size", disk.get("size_bytes"), "lsblk"),
                _row("Temperature (now)", f"{disk.get('temperature_c')} °C" if disk.get("temperature_c") is not None else None, "smart"),
                _row("Wear (now)", f"{disk.get('wear_percent')} %" if disk.get("wear_percent") is not None else None, "smart"),
                _row("Power-on hours", disk.get("power_on_hours"), "smart"),
                _row("IO scheduler (now)", (disk.get("scheduler") or "").strip("[]"), "sysfs"),
                _row("Total read", f"{ds.get('read_mib', '?')} MiB", "diskstats"),
                _row("Total written", f"{ds.get('write_mib', '?')} MiB", "diskstats"),
            ],
        })

    plat = data.get("platform") or {}
    sections.append({
        "id": "platform",
        "title": "Platform",
        "rows": [
            _row("Board", f"{(plat.get('baseboard') or {}).get('Manufacturer', '?')} {(plat.get('baseboard') or {}).get('Product Name', '')}", "dmidecode"),
            _row("BIOS", f"{(plat.get('bios') or {}).get('Version', '?')} ({(plat.get('bios') or {}).get('Release Date', '?')})", "dmidecode"),
            _row("Kernel (now)", sysinfo.get("kernel"), "system"),
            _row("PVE (now)", sysinfo.get("pveversion"), "pveversion"),
        ],
    })

    for iface in data.get("network") or []:
        eth = iface.get("ethtool") or {}
        sections.append({
            "id": f"net-{iface.get('name')}",
            "title": f"Network: {iface.get('name')}",
            "rows": [
                _row("Operstate (now)", iface.get("operstate"), "sysfs"),
                _row("Link (now)", "up" if iface.get("carrier") == 1 else "down", "sysfs"),
                _row("Speed (now)", eth.get("Speed") or iface.get("speed_mbps"), "ethtool"),
                _row("Driver", iface.get("driver"), "ethtool"),
            ],
        })

    sens = (data.get("sensors") or {}).get("normalized") or {}
    if sens.get("temperatures"):
        sections.append({
            "id": "temps",
            "title": "Temperatures",
            "rows": [_row(t.get("label") or t.get("chip"), f"{t.get('value_c')} °C", "sensors") for t in sens["temperatures"][:12]],
        })
    pwr = data.get("power") or {}
    if pwr.get("package_watts") is not None:
        sections.append({
            "id": "power",
            "title": "Power",
            "rows": [_row("CPU package (now)", f"{pwr.get('package_watts')} W", "rapl")],
        })
    return sections


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
    payload = {
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
        "storage": collect_storage(),
        "diskstats": collect_diskstats(),
        "platform": collect_platform(),
        "memory_modules": collect_memory_modules(),
        "network": collect_network(),
        "lscpu": collect_lscpu(),
        "capabilities": collect_capabilities(cpu),
        "profiles": profile_catalog(cpu),
    }
    payload["inventory"] = build_inventory(payload)
    return payload


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
        "storage": full.get("storage"),
        "diskstats": full.get("diskstats"),
        "platform": full.get("platform"),
        "memory_modules": full.get("memory_modules"),
        "network": full.get("network"),
        "inventory": full.get("inventory"),
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
