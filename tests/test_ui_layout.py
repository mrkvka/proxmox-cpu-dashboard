#!/usr/bin/env python3
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "src" / "ui"


class UiLayoutTests(unittest.TestCase):
    def test_ui_modules_exist(self):
        for name in ("pve_hw_core.js", "pve_hw_tab.js", "pve_hw_plugin.js"):
            self.assertTrue((UI / name).is_file(), name)

    def test_plugin_is_minimal_override(self):
        plugin = (UI / "pve_hw_plugin.js").read_text(encoding="utf-8")
        self.assertIn("override: 'PVE.panel.Config'", plugin)
        self.assertNotIn("HardwareView", plugin)

    def test_tab_defines_hardware_view(self):
        tab = (UI / "pve_hw_tab.js").read_text(encoding="utf-8")
        self.assertIn("PVE.node.HardwareView", tab)
        self.assertNotIn("override: 'PVE.panel.Config'", tab)

    def test_legacy_summary_removed(self):
        self.assertFalse((ROOT / "src" / "pve_node_summary.js").exists())
        self.assertFalse((ROOT / "src" / "pve_node_hardware.js").exists())


if __name__ == "__main__":
    unittest.main()
