# Changelog

## [3.1.0] — 2026-05-22

### P0 — trust & operability
- Hardware API moved to **`PVE::API2::Nodes::Hardware.pm`** (no inline Perl blob in `Nodes.pm`)
- Minimal `Nodes.pm` hook only (`require` + `register_api`); **no `thermalstate` mutation**
- **`scripts/pve-version-check.sh`** — requires Proxmox VE ≥ 9.0 and valid `Nodes.pm` anchor
- **`scripts/verify-patch.sh`** — post-install checks + optional `pvesh` `/hw` test
- **`uninstall.sh`** — restores or strips patch, removes UI + Perl module + cache, restarts `pvedaemon`
- UI **confirm dialog** before Emergency profile or reducing online CPUs
- **SECURITY.md** and compatibility matrix in README

## [3.0.0] — 2026-05-22

Stable native release: Hardware tab, live inventory, GiB disk metrics, Power-on hours in hours.

## [0.5.0] and earlier

Legacy Summary patch + HTTP API on port 8087.
