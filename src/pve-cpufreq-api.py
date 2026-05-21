#!/usr/bin/env python3
"""Proxmox CPU Dashboard API.

The API is the single control plane for the Proxmox UI and the Home Assistant
integration. It keeps the original legacy endpoints for compatibility and adds
versioned JSON endpoints under /api/v1.

Legacy:
  GET  /health
  GET  /status
  POST /cpufreq
  POST /cpus

Versioned:
  GET  /api/v1/status
  GET  /api/v1/capabilities
  GET  /api/v1/sensors
  GET  /api/v1/cpufreq
  GET  /api/v1/cpus
  GET  /api/v1/power
  GET  /api/v1/profiles
  POST /api/v1/apply
  POST /api/v1/cpufreq
  POST /api/v1/cpus
  POST /api/v1/profiles/<name>/apply

Runs on 0.0.0.0:8087 by default.
Set PVE_CPU_API_TOKEN to require a Bearer or X-API-Token value for mutations.
"""
from __future__ import annotations

import glob
import http.server
import json
import os
import platform
import re
import secrets
import shutil
import socket
import subprocess
import threading
import time
import urllib.parse

VERSION = "0.5.0"
DEFAULT_HOST = os.environ.get("PVE_CPU_API_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.environ.get("PVE_CPU_API_PORT", "8087"))
API_TOKEN = os.environ.get("PVE_CPU_API_TOKEN", "").strip()

SYS_CPU_PATH = os.environ.get("PVE_CPU_SYSFS", "/sys/devices/system/cpu")
POWERCAP_PATH = os.environ.get("PVE_CPU_POWERCAP", "/sys/class/powercap")
PROC_PATH = os.environ.get("PVE_CPU_PROC", "/proc")
SENSORS_BIN = os.environ.get("PVE_CPU_SENSORS_BIN", "sensors")


class ApiError(Exception):
    """Expected API error with an HTTP status code."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def read_text(path: str, default: str | None = None) -> str | None:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    except OSError:
        return default


def read_int(path: str, default: int | None = None) -> int | None:
    value = read_text(path)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def write_text(path: str, value: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write(str(value))


def parse_words(value: str | None) -> list[str]:
    return [part for part in (value or "").split() if part]


def parse_int_words(value: str | None) -> list[int]:
    result = []
    for part in parse_words(value):
        try:
            result.append(int(part))
        except ValueError:
            pass
    return result


def json_response(success: bool, **kwargs):
    data = {"success": success}
    data.update(kwargs)
    return data


def sanitize_id(value: str) -> str:
    value = value.lower().replace("-pci-", "_").replace(" ", "_")
    return re.sub(r"[^a-z0-9_]+", "_", value).strip("_")


def mhz(khz: int | None) -> int | None:
    return round(khz / 1000) if isinstance(khz, int) and khz > 0 else None


class PowerReader:
    """Read powercap RAPL zones and compute watts from energy deltas."""

    def __init__(self, powercap_path: str = POWERCAP_PATH, clock=time.monotonic):
        self.powercap_path = powercap_path
        self.clock = clock
        self._lock = threading.Lock()
        self._previous: dict[str, tuple[int, float]] = {}

    def zones(self) -> list[dict]:
        zones = []
        for energy_path in sorted(glob.glob(os.path.join(self.powercap_path, "*", "energy_uj"))):
            zone_path = os.path.dirname(energy_path)
            name = read_text(os.path.join(zone_path, "name"), os.path.basename(zone_path)) or os.path.basename(zone_path)
            max_energy = read_int(os.path.join(zone_path, "max_energy_range_uj"))
            zones.append({
                "id": sanitize_id(os.path.basename(zone_path) + "_" + name),
                "name": name,
                "path": zone_path,
                "energy_uj_path": energy_path,
                "max_energy_range_uj": max_energy,
            })
        return zones

    def snapshot(self) -> dict:
        readings = []
        now = self.clock()
        total_w = 0.0
        have_watts = False

        with self._lock:
            for zone in self.zones():
                energy = read_int(zone["energy_uj_path"])
                watts = None
                if energy is not None:
                    previous = self._previous.get(zone["energy_uj_path"])
                    if previous:
                        prev_energy, prev_time = previous
                        delta_energy = energy - prev_energy
                        delta_time = now - prev_time
                        if delta_energy >= 0 and delta_time > 0:
                            watts = round(delta_energy / delta_time / 1_000_000, 2)
                            total_w += watts
                            have_watts = True
                    self._previous[zone["energy_uj_path"]] = (energy, now)
                zone = dict(zone)
                zone["energy_uj"] = energy
                zone["watts"] = watts
                readings.append(zone)

        return {
            "available": bool(readings),
            "total_w": round(total_w, 2) if have_watts else None,
            "zones": readings,
        }


class HardwareController:
    """Collect hardware state and apply validated sysfs mutations."""

    def __init__(
        self,
        sys_cpu_path: str = SYS_CPU_PATH,
        proc_path: str = PROC_PATH,
        sensors_bin: str = SENSORS_BIN,
        power_reader: PowerReader | None = None,
    ):
        self.sys_cpu_path = sys_cpu_path
        self.proc_path = proc_path
        self.sensors_bin = sensors_bin
        self.power = power_reader or PowerReader()

    def cpu_ids(self) -> list[int]:
        ids = []
        for path in glob.glob(os.path.join(self.sys_cpu_path, "cpu[0-9]*")):
            match = re.search(r"cpu(\d+)$", path)
            if match:
                ids.append(int(match.group(1)))
        return sorted(ids)

    def cpu_file(self, cpu_id: int, *parts: str) -> str:
        return os.path.join(self.sys_cpu_path, f"cpu{cpu_id}", *parts)

    def cpu_online(self, cpu_id: int) -> bool:
        online_path = self.cpu_file(cpu_id, "online")
        if not os.path.exists(online_path):
            return True
        return read_text(online_path) == "1"

    def collect_cpu(self) -> dict:
        per_cpu = []
        for cpu_id in self.cpu_ids():
            cpufreq_path = self.cpu_file(cpu_id, "cpufreq")
            online = self.cpu_online(cpu_id)
            cur = read_int(os.path.join(cpufreq_path, "scaling_cur_freq"))
            min_freq = read_int(os.path.join(cpufreq_path, "scaling_min_freq"))
            max_freq = read_int(os.path.join(cpufreq_path, "scaling_max_freq"))
            hw_min = read_int(os.path.join(cpufreq_path, "cpuinfo_min_freq"))
            hw_max = read_int(os.path.join(cpufreq_path, "cpuinfo_max_freq"))
            governor = read_text(os.path.join(cpufreq_path, "scaling_governor"), "") or ""
            available_governors = parse_words(read_text(os.path.join(cpufreq_path, "scaling_available_governors"), ""))
            available_frequencies = parse_int_words(read_text(os.path.join(cpufreq_path, "scaling_available_frequencies"), ""))
            driver = read_text(os.path.join(cpufreq_path, "scaling_driver"), "") or ""

            per_cpu.append({
                "id": cpu_id,
                "online": online,
                "package_id": read_int(self.cpu_file(cpu_id, "topology", "physical_package_id")),
                "core_id": read_int(self.cpu_file(cpu_id, "topology", "core_id")),
                "thread_siblings": read_text(self.cpu_file(cpu_id, "topology", "thread_siblings_list"), "") or "",
                "frequency": {
                    "available": os.path.isdir(cpufreq_path),
                    "current_khz": cur,
                    "current_mhz": mhz(cur),
                    "min_khz": min_freq,
                    "min_mhz": mhz(min_freq),
                    "max_khz": max_freq,
                    "max_mhz": mhz(max_freq),
                    "hw_min_khz": hw_min,
                    "hw_min_mhz": mhz(hw_min),
                    "hw_max_khz": hw_max,
                    "hw_max_mhz": mhz(hw_max),
                    "governor": governor,
                    "driver": driver,
                    "available_governors": available_governors,
                    "available_frequencies_khz": available_frequencies,
                    "available_frequencies_mhz": [mhz(freq) for freq in available_frequencies],
                },
            })

        online_ids = [cpu["id"] for cpu in per_cpu if cpu["online"]]
        offline_ids = [cpu["id"] for cpu in per_cpu if not cpu["online"]]
        freq_cpus = [cpu for cpu in per_cpu if cpu["frequency"]["available"]]
        ref_cpu = next((cpu for cpu in freq_cpus if cpu["online"]), freq_cpus[0] if freq_cpus else None)
        ref_freq = ref_cpu["frequency"] if ref_cpu else {}
        current_values = [
            cpu["frequency"]["current_khz"]
            for cpu in freq_cpus
            if cpu["online"] and isinstance(cpu["frequency"]["current_khz"], int)
        ]
        avg_current = round(sum(current_values) / len(current_values)) if current_values else ref_freq.get("current_khz")

        return {
            "total": len(per_cpu),
            "online": len(online_ids),
            "offline": len(offline_ids),
            "online_ids": online_ids,
            "offline_ids": offline_ids,
            "per_cpu": per_cpu,
            "frequency": {
                "available": bool(freq_cpus),
                "current_khz": avg_current,
                "current_mhz": mhz(avg_current),
                "min_khz": ref_freq.get("min_khz"),
                "min_mhz": ref_freq.get("min_mhz"),
                "max_khz": ref_freq.get("max_khz"),
                "max_mhz": ref_freq.get("max_mhz"),
                "hw_min_khz": ref_freq.get("hw_min_khz"),
                "hw_min_mhz": ref_freq.get("hw_min_mhz"),
                "hw_max_khz": ref_freq.get("hw_max_khz"),
                "hw_max_mhz": ref_freq.get("hw_max_mhz"),
                "governor": ref_freq.get("governor", ""),
                "driver": ref_freq.get("driver", ""),
                "available_governors": ref_freq.get("available_governors", []),
                "available_frequencies_khz": ref_freq.get("available_frequencies_khz", []),
                "available_frequencies_mhz": ref_freq.get("available_frequencies_mhz", []),
                "per_core_khz": [
                    cpu["frequency"]["current_khz"]
                    for cpu in freq_cpus
                    if isinstance(cpu["frequency"]["current_khz"], int)
                ],
                "per_core_mhz": [
                    cpu["frequency"]["current_mhz"]
                    for cpu in freq_cpus
                    if isinstance(cpu["frequency"]["current_mhz"], int)
                ],
            },
        }

    def collect_sensors(self) -> dict:
        raw = {}
        errors = []
        if shutil.which(self.sensors_bin):
            try:
                result = subprocess.run(
                    [self.sensors_bin, "-jA"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    check=False,
                )
                if result.returncode == 0 and result.stdout.strip():
                    raw = json.loads(result.stdout)
                else:
                    errors.append((result.stderr or result.stdout or "sensors returned no data").strip())
            except Exception as err:
                errors.append(str(err))
        else:
            errors.append(f"{self.sensors_bin} not found")

        normalized = self.normalize_sensors(raw)
        normalized["raw"] = raw
        normalized["errors"] = errors
        normalized["available"] = bool(raw)
        return normalized

    @staticmethod
    def normalize_sensors(raw: dict) -> dict:
        temperatures = []
        fans = []
        voltages = []
        other = []

        for chip_name, features in (raw or {}).items():
            if not isinstance(features, dict):
                continue
            for feature_name, values in features.items():
                if not isinstance(values, dict):
                    continue
                for key, value in values.items():
                    if not key.endswith("_input") or not isinstance(value, (int, float)):
                        continue
                    prefix = key[:-6]
                    base = {
                        "id": sanitize_id(f"{chip_name}_{feature_name}_{prefix}"),
                        "chip": chip_name,
                        "label": feature_name,
                        "input": key,
                    }
                    if prefix.startswith("temp"):
                        entry = dict(base)
                        entry.update({
                            "value_c": round(float(value), 1),
                            "max_c": values.get(prefix + "_max"),
                            "critical_c": values.get(prefix + "_crit"),
                        })
                        temperatures.append(entry)
                    elif prefix.startswith("fan"):
                        entry = dict(base)
                        entry["rpm"] = int(value)
                        fans.append(entry)
                    elif prefix.startswith("in") or "volt" in feature_name.lower():
                        entry = dict(base)
                        entry["value_v"] = round(float(value), 3)
                        voltages.append(entry)
                    else:
                        entry = dict(base)
                        entry["value"] = value
                        other.append(entry)

        temps_flat = {}
        for item in temperatures:
            key = item["id"]
            chip = item["chip"].lower()
            label = item["label"].lower()
            if "k10temp" in chip or "coretemp" in chip:
                key = "cpu_tctl" if "tctl" in label else "cpu_" + sanitize_id(item["label"])
            elif "nvme" in chip and "composite" in label:
                key = "nvme_composite"
            elif "nvme" in chip and ("sensor 1" in label or "sensor1" in label):
                key = "nvme_sensor1"
            temps_flat[key] = item["value_c"]

        return {
            "temperatures": temperatures,
            "fans": fans,
            "voltages": voltages,
            "other": other,
            "temps": temps_flat,
        }

    def collect_power(self) -> dict:
        return self.power.snapshot()

    def collect_system(self) -> dict:
        uptime = None
        uptime_text = read_text(os.path.join(self.proc_path, "uptime"))
        if uptime_text:
            try:
                uptime = int(float(uptime_text.split()[0]))
            except (ValueError, IndexError):
                uptime = None

        try:
            loadavg = list(os.getloadavg())
        except OSError:
            loadavg = []

        pveversion = None
        if shutil.which("pveversion"):
            try:
                result = subprocess.run(["pveversion"], capture_output=True, text=True, timeout=3, check=False)
                if result.returncode == 0:
                    pveversion = result.stdout.strip()
            except Exception:
                pass

        return {
            "hostname": socket.gethostname(),
            "kernel": platform.release(),
            "machine": platform.machine(),
            "loadavg": loadavg,
            "uptime_seconds": uptime,
            "pveversion": pveversion,
        }

    def capabilities(self, cpu: dict | None = None, sensors: dict | None = None, power: dict | None = None) -> dict:
        cpu = cpu or self.collect_cpu()
        sensors = sensors or {"available": shutil.which(self.sensors_bin) is not None}
        power = power or {"available": bool(glob.glob(os.path.join(self.power.powercap_path, "*", "energy_uj")))}
        governors = cpu["frequency"].get("available_governors", [])
        writable_governor = any(
            os.access(self.cpu_file(cpu_id, "cpufreq", "scaling_governor"), os.W_OK)
            for cpu_id in cpu["online_ids"]
        )
        writable_max = any(
            os.access(self.cpu_file(cpu_id, "cpufreq", "scaling_max_freq"), os.W_OK)
            for cpu_id in cpu["online_ids"]
        )
        writable_min = any(
            os.access(self.cpu_file(cpu_id, "cpufreq", "scaling_min_freq"), os.W_OK)
            for cpu_id in cpu["online_ids"]
        )
        writable_online = any(
            os.access(self.cpu_file(cpu_id, "online"), os.W_OK)
            for cpu_id in cpu["offline_ids"] + cpu["online_ids"]
            if cpu_id != 0
        )
        return {
            "sensors": bool(sensors.get("available")),
            "power_rapl": bool(power.get("available")),
            "cpufreq": bool(cpu["frequency"].get("available")),
            "set_governor": bool(governors and writable_governor),
            "set_min_frequency": writable_min,
            "set_max_frequency": writable_max,
            "set_online_cpus": writable_online,
            "profiles": True,
            "auth_required_for_mutations": bool(API_TOKEN),
        }

    def collect_status(self, include_power: bool = True) -> dict:
        cpu = self.collect_cpu()
        sensors = self.collect_sensors()
        power = self.collect_power() if include_power else {"available": False, "total_w": None, "zones": []}
        return {
            "meta": {
                "name": "Proxmox CPU Dashboard API",
                "version": VERSION,
                "collected_at": int(time.time()),
            },
            "system": self.collect_system(),
            "cpu": cpu,
            "sensors": sensors,
            "power": power,
            "profiles": self.profile_catalog(cpu),
            "capabilities": self.capabilities(cpu=cpu, sensors=sensors, power=power),
        }

    def legacy_status(self) -> dict:
        full = self.collect_status()
        freq = full["cpu"]["frequency"]
        return {
            "temps": full["sensors"].get("temps", {}),
            "cpufreq": {
                "current_khz": freq.get("current_khz") or 0,
                "min_khz": freq.get("min_khz") or 0,
                "max_khz": freq.get("max_khz") or 0,
                "hw_min_khz": freq.get("hw_min_khz") or 0,
                "hw_max_khz": freq.get("hw_max_khz") or 0,
                "governor": freq.get("governor", ""),
                "available_governors": freq.get("available_governors", []),
                "available_frequencies": freq.get("available_frequencies_khz", []),
            },
            "cpus": {
                "online": full["cpu"]["online"],
                "total": full["cpu"]["total"],
                "offline": full["cpu"]["offline"],
            },
            "power_w": full["power"].get("total_w"),
            "per_core_mhz": freq.get("per_core_mhz", []),
        }

    def profile_catalog(self, cpu: dict | None = None) -> dict:
        cpu = cpu or self.collect_cpu()
        freq = cpu["frequency"]
        governors = freq.get("available_governors", [])
        hw_min = freq.get("hw_min_khz") or freq.get("min_khz") or 0
        hw_max = freq.get("hw_max_khz") or freq.get("max_khz") or 0
        total = cpu["total"] or 1

        def governor(*preferred):
            for name in preferred:
                if name in governors:
                    return name
            return governors[0] if governors else None

        def percent(value):
            if not hw_max:
                return None
            target = int(hw_max * value)
            if hw_min:
                target = max(hw_min, target)
            return int(round(target / 100000) * 100000)

        return {
            "performance": {
                "description": "All logical CPUs online, highest advertised CPU frequency.",
                "settings": {
                    "online_cpus": total,
                    "governor": governor("performance", "schedutil", "ondemand"),
                    "max_freq_khz": hw_max or None,
                },
            },
            "balanced": {
                "description": "All logical CPUs online, moderate max frequency for daily use.",
                "settings": {
                    "online_cpus": total,
                    "governor": governor("conservative", "schedutil", "ondemand", "performance"),
                    "max_freq_khz": percent(0.65),
                },
            },
            "powersave": {
                "description": "Reduced logical CPU count and lower max frequency for UPS or heat events.",
                "settings": {
                    "online_cpus": max(1, total // 2),
                    "governor": governor("powersave", "schedutil", "conservative"),
                    "max_freq_khz": percent(0.50),
                },
            },
            "emergency": {
                "description": "Minimum practical CPU footprint for long UPS runtime.",
                "settings": {
                    "online_cpus": max(1, total // 4),
                    "governor": governor("powersave", "schedutil"),
                    "max_freq_khz": hw_min or percent(0.35),
                },
            },
            "restore": {
                "description": "Restore all logical CPUs and max frequency.",
                "settings": {
                    "online_cpus": total,
                    "governor": governor("schedutil", "conservative", "ondemand", "performance"),
                    "max_freq_khz": hw_max or None,
                },
            },
        }

    def resolve_profile(self, name: str) -> dict:
        profiles = self.profile_catalog()
        profile = profiles.get(name)
        if not profile:
            raise ApiError(f"unknown profile: {name}", 404)
        return {k: v for k, v in profile["settings"].items() if v is not None}

    def validate_settings(self, settings: dict, cpu: dict | None = None) -> dict:
        cpu = cpu or self.collect_cpu()
        freq = cpu["frequency"]
        result = {}

        governor = settings.get("governor")
        if governor:
            governor = str(governor).strip()
            available = freq.get("available_governors", [])
            if available and governor not in available:
                raise ApiError(f"invalid governor '{governor}', available: {', '.join(available)}")
            result["governor"] = governor

        for src, dst in (
            ("max_freq_khz", "max_freq_khz"),
            ("max_freq", "max_freq_khz"),
            ("min_freq_khz", "min_freq_khz"),
            ("min_freq", "min_freq_khz"),
        ):
            if src in settings and settings[src] not in (None, ""):
                try:
                    value = int(settings[src])
                except (TypeError, ValueError):
                    raise ApiError(f"{src} must be an integer kHz value")
                if value < 10000:
                    value *= 1000
                if value <= 0:
                    raise ApiError(f"{src} must be positive")
                result[dst] = value

        hw_min = freq.get("hw_min_khz") or freq.get("min_khz")
        hw_max = freq.get("hw_max_khz") or freq.get("max_khz")
        for key in ("min_freq_khz", "max_freq_khz"):
            value = result.get(key)
            if value is None:
                continue
            if hw_min and value < hw_min:
                raise ApiError(f"{key}={value} is below hardware minimum {hw_min}")
            if hw_max and value > hw_max:
                raise ApiError(f"{key}={value} is above hardware maximum {hw_max}")
        if result.get("min_freq_khz") and result.get("max_freq_khz"):
            if result["min_freq_khz"] > result["max_freq_khz"]:
                raise ApiError("min_freq_khz cannot be greater than max_freq_khz")

        if "online_cpus" in settings and settings["online_cpus"] not in (None, ""):
            try:
                target = int(settings["online_cpus"])
            except (TypeError, ValueError):
                raise ApiError("online_cpus must be an integer")
            if target < 1:
                raise ApiError("online_cpus must be at least 1")
            if cpu["total"] and target > cpu["total"]:
                raise ApiError(f"online_cpus={target} is above total CPU count {cpu['total']}")
            result["online_cpus"] = target

        if parse_bool(settings.get("restore_all_cpus")):
            result["online_cpus"] = cpu["total"]

        if not result:
            raise ApiError("no settings supplied")
        return result

    def writable_cpufreq_cpu_ids(self) -> list[int]:
        return [
            cpu_id
            for cpu_id in self.cpu_ids()
            if self.cpu_online(cpu_id) and os.path.isdir(self.cpu_file(cpu_id, "cpufreq"))
        ]

    def set_online_cpus(self, target: int, dry_run: bool = False) -> dict:
        ids = self.cpu_ids()
        if not ids:
            raise ApiError("no CPUs found", 500)
        if target < 1 or target > len(ids):
            raise ApiError(f"online_cpus must be between 1 and {len(ids)}")

        writes = []
        for index, cpu_id in enumerate(ids):
            if cpu_id == 0:
                continue
            online_file = self.cpu_file(cpu_id, "online")
            if not os.path.exists(online_file):
                continue
            desired = "1" if index < target else "0"
            if read_text(online_file) == desired:
                continue
            writes.append({"path": online_file, "value": desired, "cpu": cpu_id})
            if not dry_run:
                write_text(online_file, desired)
        return {"operation": "set_online_cpus", "target": target, "writes": writes}

    def write_cpufreq_value(self, filename: str, value: str | int, dry_run: bool = False) -> dict:
        writes = []
        for cpu_id in self.writable_cpufreq_cpu_ids():
            path = self.cpu_file(cpu_id, "cpufreq", filename)
            if not os.path.exists(path):
                continue
            writes.append({"path": path, "value": str(value), "cpu": cpu_id})
            if not dry_run:
                write_text(path, str(value))
        if not writes:
            raise ApiError(f"no writable {filename} files found", 500)
        return {"operation": "write_" + filename, "value": value, "writes": writes}

    def apply_settings(self, settings: dict, dry_run: bool = False) -> dict:
        settings = {
            key: (value[0] if isinstance(value, list) and value else value)
            for key, value in settings.items()
        }
        profile_name = settings.get("profile")
        merged = {}
        if profile_name:
            merged.update(self.resolve_profile(str(profile_name)))
        merged.update({k: v for k, v in settings.items() if k != "profile"})

        before_cpu = self.collect_cpu()
        validated = self.validate_settings(merged, before_cpu)
        actions = []

        target_cpus = validated.get("online_cpus")
        if target_cpus and target_cpus > before_cpu["online"]:
            actions.append(self.set_online_cpus(target_cpus, dry_run=dry_run))

        if "max_freq_khz" in validated and "min_freq_khz" in validated:
            current_min = before_cpu["frequency"].get("min_khz") or 0
            if validated["min_freq_khz"] > (before_cpu["frequency"].get("max_khz") or 0):
                actions.append(self.write_cpufreq_value("scaling_max_freq", validated["max_freq_khz"], dry_run=dry_run))
                actions.append(self.write_cpufreq_value("scaling_min_freq", validated["min_freq_khz"], dry_run=dry_run))
            elif validated["max_freq_khz"] < current_min:
                actions.append(self.write_cpufreq_value("scaling_min_freq", validated["min_freq_khz"], dry_run=dry_run))
                actions.append(self.write_cpufreq_value("scaling_max_freq", validated["max_freq_khz"], dry_run=dry_run))
            else:
                actions.append(self.write_cpufreq_value("scaling_min_freq", validated["min_freq_khz"], dry_run=dry_run))
                actions.append(self.write_cpufreq_value("scaling_max_freq", validated["max_freq_khz"], dry_run=dry_run))
        else:
            if "min_freq_khz" in validated:
                actions.append(self.write_cpufreq_value("scaling_min_freq", validated["min_freq_khz"], dry_run=dry_run))
            if "max_freq_khz" in validated:
                actions.append(self.write_cpufreq_value("scaling_max_freq", validated["max_freq_khz"], dry_run=dry_run))

        if "governor" in validated:
            actions.append(self.write_cpufreq_value("scaling_governor", validated["governor"], dry_run=dry_run))

        if target_cpus and target_cpus <= before_cpu["online"]:
            actions.append(self.set_online_cpus(target_cpus, dry_run=dry_run))

        return json_response(
            True,
            dry_run=dry_run,
            profile=profile_name,
            settings=validated,
            actions=actions,
            status=self.legacy_status() if not dry_run else None,
        )


CONTROLLER = HardwareController()


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("1", "true", "yes", "on")


def first_value(data: dict, *names, default=None):
    for name in names:
        if name in data:
            value = data[name]
            if isinstance(value, list):
                return value[0] if value else default
            return value
    return default


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "PVECPUAPI/" + VERSION

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-API-Token")

    def _send_json(self, code: int, obj: dict):
        body = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        if not API_TOKEN:
            return True
        header = self.headers.get("Authorization", "")
        token = self.headers.get("X-API-Token", "")
        if header.lower().startswith("bearer "):
            token = header.split(" ", 1)[1].strip()
        return secrets.compare_digest(token, API_TOKEN)

    def _body(self) -> dict:
        parsed = urllib.parse.urlparse(self.path)
        params = {k: v for k, v in urllib.parse.parse_qs(parsed.query).items()}
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode() if length > 0 else ""
        content_type = (self.headers.get("Content-Type") or "").lower()
        if "json" in content_type and raw:
            try:
                data = json.loads(raw)
                if isinstance(data, dict):
                    params.update(data)
            except json.JSONDecodeError:
                raise ApiError("invalid JSON body")
        elif raw:
            params.update(urllib.parse.parse_qs(raw))
        return params

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        try:
            if path == "/health":
                self._send_json(200, {"ok": True, "version": VERSION})
            elif path == "/status":
                self._send_json(200, CONTROLLER.legacy_status())
            elif path in ("/api/v1", "/api/v1/"):
                self._send_json(200, self.api_index())
            elif path == "/api/v1/status":
                self._send_json(200, CONTROLLER.collect_status())
            elif path == "/api/v1/capabilities":
                self._send_json(200, CONTROLLER.capabilities())
            elif path == "/api/v1/sensors":
                self._send_json(200, CONTROLLER.collect_sensors())
            elif path == "/api/v1/cpufreq":
                self._send_json(200, CONTROLLER.collect_cpu()["frequency"])
            elif path == "/api/v1/cpus":
                cpu = CONTROLLER.collect_cpu()
                self._send_json(200, {k: cpu[k] for k in ("total", "online", "offline", "online_ids", "offline_ids", "per_cpu")})
            elif path == "/api/v1/power":
                self._send_json(200, CONTROLLER.collect_power())
            elif path == "/api/v1/profiles":
                self._send_json(200, CONTROLLER.profile_catalog())
            else:
                self._send_json(404, {"error": "not found"})
        except ApiError as err:
            self._send_json(err.status, json_response(False, error=str(err)))
        except Exception as err:
            self._send_json(500, json_response(False, error=str(err)))

    def do_POST(self):
        path = urllib.parse.urlparse(self.path).path.rstrip("/") or "/"
        if not self._authorized():
            self._send_json(401, json_response(False, error="unauthorized"))
            return
        try:
            params = self._body()
            dry_run = parse_bool(first_value(params, "dry_run", default=False))

            if path in ("/cpufreq", "/api/v1/cpufreq"):
                settings = {
                    "governor": first_value(params, "governor", default=""),
                    "max_freq_khz": first_value(params, "max_freq_khz", "max_freq", default=""),
                    "min_freq_khz": first_value(params, "min_freq_khz", "min_freq", default=""),
                    "restore_all_cpus": parse_bool(first_value(params, "restore_all_cpus", default=False)),
                }
                self._send_json(200, CONTROLLER.apply_settings(settings, dry_run=dry_run))
            elif path in ("/cpus", "/api/v1/cpus"):
                self._send_json(200, CONTROLLER.apply_settings({
                    "online_cpus": first_value(params, "online_cpus", "online", default=""),
                }, dry_run=dry_run))
            elif path == "/api/v1/apply":
                self._send_json(200, CONTROLLER.apply_settings(params, dry_run=dry_run))
            elif path.startswith("/api/v1/profiles/") and path.endswith("/apply"):
                name = path.split("/")[4]
                self._send_json(200, CONTROLLER.apply_settings({"profile": name}, dry_run=dry_run))
            else:
                self._send_json(404, {"error": "not found"})
        except ApiError as err:
            self._send_json(err.status, json_response(False, error=str(err)))
        except Exception as err:
            self._send_json(500, json_response(False, error=str(err)))

    @staticmethod
    def api_index() -> dict:
        return {
            "name": "Proxmox CPU Dashboard API",
            "version": VERSION,
            "endpoints": {
                "GET": [
                    "/health",
                    "/status",
                    "/api/v1/status",
                    "/api/v1/capabilities",
                    "/api/v1/sensors",
                    "/api/v1/cpufreq",
                    "/api/v1/cpus",
                    "/api/v1/power",
                    "/api/v1/profiles",
                ],
                "POST": [
                    "/cpufreq",
                    "/cpus",
                    "/api/v1/apply",
                    "/api/v1/cpufreq",
                    "/api/v1/cpus",
                    "/api/v1/profiles/<name>/apply",
                ],
            },
        }

    def log_message(self, format, *args):
        pass


def main():
    server = http.server.ThreadingHTTPServer((DEFAULT_HOST, DEFAULT_PORT), Handler)
    print(f"Proxmox CPU Dashboard API {VERSION} listening on {DEFAULT_HOST}:{DEFAULT_PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
