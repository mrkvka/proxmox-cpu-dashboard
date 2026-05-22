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


if __name__ == "__main__":
    unittest.main()
