# Changelog

## [3.2.0] — 2026-05-22

### P1 — API-first cleanup
- **docs/API.md** — integration guide (tokens, endpoints, examples); no Home Assistant in this repo
- Removed **pve-hwinfo.sh** (thermalstate path dropped in v3.1)
- **audit-hardware.sh** uses `pvesh` `/hw` instead of legacy `:8087`
- Removed legacy **test_pve_cpufreq_api.py**; added **test_collect_formatters.py**
- **CI** (GitHub Actions): py_compile, unittest, shellcheck, perl -c
- README focused on native API; external clients link to API.md only

## [3.1.0] — 2026-05-22

### P0 — trust & operability
- Hardware API in `PVE::API2::Nodes::Hardware.pm`; minimal `Nodes.pm` hook on Nodeinfo
- `scripts/pve-version-check.sh`, `scripts/verify-patch.sh`, full `uninstall.sh`
- CPU safety confirm for Emergency / fewer online CPUs
- SECURITY.md, compatibility matrix

## [3.0.0] — 2026-05-22

Stable: Hardware tab, live inventory, GiB metrics, Power-on hours in hours.

## [0.5.0] and earlier

Legacy HTTP API on port 8087.

