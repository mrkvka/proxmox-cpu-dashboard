import importlib.util
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
API_PATH = ROOT / "src" / "pve-cpufreq-api.py"

spec = importlib.util.spec_from_file_location("pve_cpufreq_api", API_PATH)
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(value), encoding="utf-8")


class StaticPower:
    powercap_path = "/does/not/matter"

    def snapshot(self):
        return {"available": False, "total_w": None, "zones": []}


class CpuApiTests(unittest.TestCase):
    def make_controller(self):
        tmp = tempfile.TemporaryDirectory()
        root = pathlib.Path(tmp.name)
        sys_cpu = root / "sys" / "devices" / "system" / "cpu"
        proc = root / "proc"
        write(proc / "uptime", "123.45 67.89")

        for cpu_id, online in ((0, None), (1, "1"), (2, "0"), (3, "1")):
            cpu = sys_cpu / f"cpu{cpu_id}"
            (cpu / "cpufreq").mkdir(parents=True)
            if online is not None:
                write(cpu / "online", online)
            write(cpu / "topology" / "physical_package_id", "0")
            write(cpu / "topology" / "core_id", str(cpu_id // 2))
            write(cpu / "topology" / "thread_siblings_list", f"{cpu_id}")
            write(cpu / "cpufreq" / "scaling_governor", "schedutil")
            write(cpu / "cpufreq" / "scaling_available_governors", "performance schedutil powersave")
            write(cpu / "cpufreq" / "scaling_cur_freq", "1800000")
            write(cpu / "cpufreq" / "scaling_min_freq", "400000")
            write(cpu / "cpufreq" / "scaling_max_freq", "3000000")
            write(cpu / "cpufreq" / "cpuinfo_min_freq", "400000")
            write(cpu / "cpufreq" / "cpuinfo_max_freq", "3000000")
            write(cpu / "cpufreq" / "scaling_available_frequencies", "400000 1800000 3000000")
            write(cpu / "cpufreq" / "scaling_driver", "amd-pstate")

        controller = api.HardwareController(
            sys_cpu_path=str(sys_cpu),
            proc_path=str(proc),
            sensors_bin="missing-sensors-bin",
            power_reader=StaticPower(),
        )
        self.addCleanup(tmp.cleanup)
        return controller, sys_cpu

    def test_collect_cpu_from_fake_sysfs(self):
        controller, _ = self.make_controller()
        cpu = controller.collect_cpu()

        self.assertEqual(cpu["total"], 4)
        self.assertEqual(cpu["online"], 3)
        self.assertEqual(cpu["offline_ids"], [2])
        self.assertEqual(cpu["frequency"]["governor"], "schedutil")
        self.assertEqual(cpu["frequency"]["current_mhz"], 1800)
        self.assertEqual(cpu["frequency"]["available_governors"], ["performance", "schedutil", "powersave"])

    def test_normalize_sensors(self):
        raw = {
            "k10temp-pci-00c3": {"Tctl": {"temp1_input": 65.25, "temp1_crit": 95.0}},
            "nvme-pci-0100": {"Composite": {"temp1_input": 44.2}},
            "nct6798-isa-0a20": {"fan1": {"fan1_input": 934}},
        }

        sensors = api.HardwareController.normalize_sensors(raw)

        self.assertEqual(sensors["temps"]["cpu_tctl"], 65.2)
        self.assertEqual(sensors["temps"]["nvme_composite"], 44.2)
        self.assertEqual(sensors["fans"][0]["rpm"], 934)

    def test_apply_frequency_writes_online_cpus_only(self):
        controller, sys_cpu = self.make_controller()

        result = controller.apply_settings({"governor": "powersave", "max_freq_khz": 1800000})

        self.assertTrue(result["success"])
        self.assertEqual((sys_cpu / "cpu0" / "cpufreq" / "scaling_governor").read_text(), "powersave")
        self.assertEqual((sys_cpu / "cpu1" / "cpufreq" / "scaling_max_freq").read_text(), "1800000")
        self.assertEqual((sys_cpu / "cpu2" / "cpufreq" / "scaling_governor").read_text(), "schedutil")

    def test_dry_run_profile_does_not_write(self):
        controller, sys_cpu = self.make_controller()

        result = controller.apply_settings({"profile": "powersave"}, dry_run=True)

        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        self.assertEqual((sys_cpu / "cpu1" / "online").read_text(), "1")
        self.assertGreaterEqual(len(result["actions"]), 1)

    def test_legacy_status_shape_is_home_assistant_friendly(self):
        controller, _ = self.make_controller()

        legacy = controller.legacy_status()

        self.assertIn("temps", legacy)
        self.assertIn("cpufreq", legacy)
        self.assertIn("cpus", legacy)
        self.assertIn("per_core_mhz", legacy)
        self.assertEqual(legacy["cpus"]["total"], 4)


if __name__ == "__main__":
    unittest.main()
