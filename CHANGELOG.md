# Changelog

## [3.4.2] — 2026-05-22

### System power estimate

- `power.system_watts` — whole-node estimate (measured RAPL/sensors, hybrid, or heuristic)
- `power.method` / `power.confidence`, `power.estimate` breakdown (CPU TDP, memory, storage, platform)
- Inventory **Power** section shows system total plus component estimates

## [3.4.0] — 2026-05-22

### Split packages for distribution

- **proxmox-node-hw-api** — `install-api.sh`, `uninstall-api.sh`, `build-deb-api.sh`
- **proxmox-node-hw-ui** — `install-ui.sh`, `uninstall-ui.sh`, `build-deb-ui.sh` (Depends on API same version)
- `install.sh` / `uninstall.sh` — convenience wrappers (API+UI)
- `scripts/verify-ui.sh` — UI install checks
- `make deb-api` / `make deb-ui` / `make deb`

## [3.3.0]

Product quality: VERSION file, `/usr/share/pve-node-hw-api/`, `make deb`, warnings[].

## [3.2.0]

API-first docs, CI, no HA in repo.

## [3.1.0]

P0: Hardware.pm, verify scripts, CPU confirm.

## [3.0.0]

Stable Hardware tab and live inventory.

## [0.5.0]

Legacy HTTP API on port 8087.
