# Changelog

## [3.5.3] — 2026-05-23

### Public release

- GitHub Releases + `.deb` assets, CI release workflow, issue templates, README screenshots

### Network inventory

- One **Network** section with subgroups per interface (Ethernet, Wi-Fi, bridge, …)
- Detect kind/MAC/wireless mode; sort Ethernet before Wi-Fi

## [3.5.2] — 2026-05-23

### Fix

- Hardware tab only on **node** config (`PVE.node.Config`), not on VM/CT guests

## [3.5.1] — 2026-05-23

### Fix

- `install-ui.sh`: script tags were not injected (`\${tag}` never expanded); use awk append

## [3.5.0] — 2026-05-22

### P2: UI plugin polish

- Split UI into `src/ui/`: `pve_hw_core.js`, `pve_hw_tab.js`, `pve_hw_plugin.js`
- `install-ui.sh` migrates legacy `pve_node_*.js` names; chained script load order
- `docs/PLUGIN.md`, `docs/ROADMAP.md`

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
