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

    def test_rapl_zone_role(self):
        self.assertEqual(mod._rapl_zone_role("package-0", "/sys/class/powercap/intel-rapl:0"), "package")
        self.assertEqual(mod._rapl_zone_role("", "/sys/class/powercap/amd-rapl"), "package")
        self.assertEqual(mod._rapl_zone_role("psys", "/sys/class/powercap/intel-rapl:0:psys"), "psys")
        self.assertEqual(mod._rapl_zone_role("core", "/sys/class/powercap/intel-rapl:0:core"), "core")

    def test_parse_tdp_amd_4800h(self):
        tdp, source = mod._parse_tdp_w(
            cpu={"per_cpu": [{"online": True, "topology": {"core_id": i // 2}} for i in range(16)]},
            processor_dmi={},
            system={"processor": "AMD Ryzen 7 4800H with Radeon Graphics"},
        )
        self.assertEqual(tdp, 45.0)
        self.assertEqual(source, "amd model suffix")

    def test_physical_core_count(self):
        cpu = {
            "per_cpu": [
                {"online": True, "topology": {"core_id": 0}},
                {"online": True, "topology": {"core_id": 0}},
                {"online": True, "topology": {"core_id": 1}},
                {"online": False, "topology": {"core_id": 2}},
            ]
        }
        self.assertEqual(mod._physical_core_count(cpu), 2)
        self.assertEqual(mod._rapl_zone_role("package-0", "/sys/class/powercap/intel-rapl:0"), "package")
        self.assertEqual(mod._rapl_zone_role("", "/sys/class/powercap/amd-rapl"), "package")
        self.assertEqual(mod._rapl_zone_role("psys", "/sys/class/powercap/intel-rapl:0:psys"), "psys")
        self.assertEqual(mod._rapl_zone_role("core", "/sys/class/powercap/intel-rapl:0:core"), "core")

    def test_resolve_power_totals_no_double_count(self):
        est = {"memory_w": 11.2, "storage_w": 7.0, "platform_w": 25.0, "load_total_w": 180.0}
        system_w, method, _conf = mod._resolve_power_totals(
            package_watts=62.5,
            psys_watts=None,
            estimate=est,
        )
        self.assertEqual(method, "hybrid")
        self.assertAlmostEqual(system_w, 105.7)

        system_w, method, _conf = mod._resolve_power_totals(
            package_watts=62.5,
            psys_watts=140.0,
            estimate=est,
        )
        self.assertEqual(method, "measured")
        self.assertEqual(system_w, 140.0)

    def test_assess_thermal_throttle(self):
        hot = mod.assess_thermal_state(
            tctl_c=99.0, cpu_pct=99.0, current_mhz=1400, max_mhz=2900, package_watts=45.0
        )
        self.assertEqual(hot["level"], "throttle")
        self.assertIn("ТРОТТЛИНГ", hot["label"])

        ok = mod.assess_thermal_state(
            tctl_c=55.0, cpu_pct=10.0, current_mhz=1400, max_mhz=2900
        )
        self.assertEqual(ok["level"], "ok")

    def test_extract_cpu_tctl(self):
        sensors = {
            "normalized": {
                "temperatures": [
                    {"label": "Composite", "value_c": 50.0, "chip": "nvme"},
                    {"label": "Tctl", "value_c": 81.5, "chip": "k10temp-pci-00c3"},
                ]
            }
        }
        self.assertEqual(mod._extract_cpu_tctl(sensors), 81.5)

        zone = {"max_energy_range_uj": 10_000_000_000, "_prev_energy_uj": 9_999_000_000}
        watts = mod._energy_delta_w(zone, 500_000_000, 1.0)
        self.assertIsNotNone(watts)
        self.assertGreater(watts, 0)

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
