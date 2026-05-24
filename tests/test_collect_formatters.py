#!/usr/bin/env python3
"""Unit tests for pve-hw-collect formatting helpers."""
from __future__ import annotations

import importlib.util
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
COLLECT = ROOT / "src" / "pve-hw-collect.py"

spec = importlib.util.spec_from_file_location("pve_hw_collect", COLLECT)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


class FormatterTests(unittest.TestCase):
    def test_nvme_units_to_gib(self):
        self.assertAlmostEqual(mod._nvme_units_to_gib(1), 512000 / (1024**3), places=5)

    def test_fmt_gib_tib(self):
        self.assertIn("GiB", mod._fmt_gib(100))
        self.assertIn("TiB", mod._fmt_gib(2048))

    def test_fmt_power_on_hours(self):
        self.assertIn("21990 h", mod._fmt_power_on_hours(21990))

    def test_fmt_mib_to_gib(self):
        self.assertIn("GiB", mod._fmt_mib_to_gib(1024))
    def test_estimate_system_power(self):
        est = mod.estimate_system_power(
            cpu={"online": 8, "total": 8},
            memory_modules=[{"size": "32 GiB"}],
            storage=[{"rotational": "0"}, {"rotational": "1"}],
            processor_dmi={"Max Power": "95 W"},
            system={"loadavg": [4.0]},
            rapl_breakdown=[],
        )
        self.assertEqual(est["cpu_tdp_w"], 95.0)
        self.assertEqual(est["memory_w"], round(32 * 0.35, 1))
        self.assertEqual(est["storage_w"], 10.5)
        self.assertGreater(est["load_total_w"], est["idle_total_w"])

    def test_network_iface_kind(self):
        self.assertEqual(mod._network_iface_kind("wlan0", "/nonexistent"), "Wi-Fi")
        self.assertEqual(mod._network_iface_kind("eth0", "/nonexistent"), "Ethernet")

    def test_network_inventory_subgroup(self):
        inv = mod.build_inventory({
            "network": [
                {"name": "eth0", "kind": "Ethernet", "driver": "igb", "mac": "aa", "operstate": "up", "carrier": 1, "ethtool": {}},
                {"name": "wlan0", "kind": "Wi-Fi", "driver": "iwlwifi", "mac": "bb", "operstate": "down", "ethtool": {}},
            ],
        })
        net = next(s for s in inv if s.get("id") == "network")
        self.assertEqual(len(net["subgroups"]), 2)
        self.assertEqual(net["subgroups"][0]["id"], "eth0")
        self.assertNotIn("net-eth0", [s.get("id") for s in inv])


if __name__ == "__main__":
    unittest.main()
