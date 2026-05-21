#!/usr/bin/env python3
"""Apply validated CPU / hardware settings on the local Proxmox node."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

COLLECT = Path("/usr/local/bin/pve-hw-collect.py")
SETFREQ = Path("/usr/local/bin/pve-cpufreq-set.sh")
SETCPUS = Path("/usr/local/bin/pve-cpus-set.sh")


def load_catalog() -> dict:
    proc = subprocess.run(
        [str(COLLECT)],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(proc.stdout)["profiles"]


def resolve_profile(name: str) -> dict:
    profiles = load_catalog()
    if name not in profiles:
        raise SystemExit(f"unknown profile: {name}")
    return dict(profiles[name]["settings"])


def run_script(path: Path, *args: str) -> None:
    proc = subprocess.run([str(path), *args], capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode != 0:
        msg = (proc.stderr or proc.stdout or "command failed").strip()
        raise SystemExit(msg)


def apply_settings(settings: dict) -> dict:
    governor = settings.get("governor")
    max_freq = settings.get("max_freq_khz") or settings.get("max_freq")
    online = settings.get("online_cpus") or settings.get("online")

    if online is not None:
        run_script(SETCPUS, str(int(online)))

    gov = str(governor) if governor else ""
    freq = str(int(max_freq)) if max_freq else ""
    if gov or freq:
        run_script(SETFREQ, gov, freq)

    proc = subprocess.run([str(COLLECT), "--compact"], capture_output=True, text=True, timeout=30, check=True)
    return json.loads(proc.stdout)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", help="performance|balanced|powersave|emergency|restore")
    parser.add_argument("--governor")
    parser.add_argument("--max-freq-khz", type=int)
    parser.add_argument("--online-cpus", type=int)
    parser.add_argument("--json", help="JSON settings object")
    args = parser.parse_args()

    settings: dict = {}
    if args.json:
        settings.update(json.loads(args.json))
    if args.profile:
        settings.update(resolve_profile(args.profile))
    if args.governor:
        settings["governor"] = args.governor
    if args.max_freq_khz is not None:
        settings["max_freq_khz"] = args.max_freq_khz
    if args.online_cpus is not None:
        settings["online_cpus"] = args.online_cpus

    if not settings:
        raise SystemExit("no settings to apply")

    result = apply_settings(settings)
    json.dump({"success": True, "applied": settings, "state": result}, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
